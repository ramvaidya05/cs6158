# Translation accuracy and bounded environment repair

Use Python 3.12 or newer. On this Mac, `python3` resolves to 3.9;
`/opt/homebrew/bin/python3.12` is the working interpreter. Docker Desktop must be
running. The Java reference remains a trusted local process; generated Python
runs only in disposable containers.

## Reproduce and prepare

```sh
python3.12 scripts/bootstrap.py
python3.12 scripts/verify.py --archive
python3.12 scripts/build_containers.py
python3.12 -m migration_lab freeze --output evaluator-private/pilot-v1.json
python3.12 scripts/verify_isolation.py --suite evaluator-private/pilot-v1.json
```

`freeze` refuses to overwrite a suite. It creates a fresh random seed, 26 visible
cases per task, and 140/124/131 withheld cases for Levenshtein/normalized/JaroWinkler.
It repeats the Java oracle and saves inputs, outputs, source identity, comparator
hash, and generator hash. Explicit cases cover UTF-16 strings, nulls, combining
characters, zero/negative/32-bit limit boundaries, long prefixes, thresholds, and
high-overlap strings that exercise source-specific numeric behavior. Random cases
supplement these strata. Existing files can be loaded without regenerating them.

The suite lives in ignored `evaluator-private/`. Experiment archives contain a
copy for audit/reproduction; access to those archives therefore reveals scored
cases. Do not use an exposed archive as a fresh blind holdout. The translation
model never receives this file, and candidate containers never mount it.

## Run the live Levenshtein study

Set `OPENAI_API_KEY` through your secret manager, without committing or printing
it. Or run `python3.12 scripts/configure_key.py`: it prompts without echo and writes
only the ignored local `.env` with owner-only permissions. CLI experiment/run and
the scripts load that file without evaluating shell commands. Alternatively, `scripts/live_pilot.py` prompts without terminal echo and keeps
the key only in process memory.

```sh
python3.12 -m migration_lab experiment \
  --suite evaluator-private/pilot-v1.json --backend openai \
  --model gpt-5.6-sol --reasoning-effort medium \
  --task levenshtein --trials 3 --max-repairs 5 \
  --max-spend-usd 1 --archive
```

The experiment freezes task/trial counts and budgets before generation. Each
replicate generates one initial translation in a healthy environment, then reuses
that exact response in the code-repair and environment-repair arms. A successful
initial candidate needs no repair. Different trials make fresh generation calls;
reusing the initial candidate within a pair is not counted as fresh inference.

All selections across all trials/arms freeze before any withheld scoring. Only
visible failures enter repair prompts. Every repair reruns all visible cases in
both runtimes; a checkpoint cannot lose a previously passing case. A failed API
repair is retained and stops further repairs while preserving the best checkpoint.
An initial generation failure leaves the paired arms unvalidated. Failures in one
trial do not abort the rest of the batch. No silent API retries occur.

The model name is explicit. Resolved model identity, actual usage, prompts,
responses, generated code, runtime results, and state transitions are saved. The
adapter distinguishes authentication/access errors, rate limits, refusal,
incomplete output, malformed output, transport errors, and timeouts. It rejects a
changed resolved model identity within the experiment.

GPT-5.6 Sol's default price settings are $4/M input and $20/M output, verified
against the [official model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
on October 19, 2026. Other models require explicit price arguments. Reservations
use the serialized request's UTF-8 byte count plus 4096 as a conservative input
allowance, a 1.25x input premium, and the requested maximum output. Known usage
settles this reservation conservatively; failed calls with unknown usage retain
it. `spend.json` is an estimate at the configured prices, not a provider-enforced
billing limit. The default is $1 for the entire batch, not $1 per task or arm.

### Gemini backend

`--backend gemini` calls the Gemini API `generateContent` endpoint with a JSON
schema response. It reads the key only from `GEMINI_API_KEY` in the process
environment; keep it outside the repository. `--reasoning-effort` maps to
Gemini's thinking level. Thinking tokens count toward `--max-output-tokens`,
so allow more headroom than for OpenAI. Prices are always explicit; on the
free tier, pass the paid list rates so the budget still caps spend if billing
is enabled.

```sh
GEMINI_API_KEY=... python3.12 -m migration_lab experiment \
  --suite evaluator-private/pilot-v1.json --backend gemini \
  --model gemini-3.8-flash --reasoning-effort medium \
  --input-usd-per-million 0.75 --output-usd-per-million 3.75 \
  --task levenshtein --trials 3 --max-repairs 5 \
  --max-output-tokens 16384 --output-token-budget 98304 \
  --max-spend-usd 1 --archive
```

Gemini 3.8 Flash prices ($0.75/M input, $3.75/M output through December 31,
2026) and free-tier availability were checked against the official pricing page
on October 19, 2026. Do not edit files under `migration_lab/`, `tests/`,
`scripts/` or other protected folders while a run is in progress; the integrity
guard will invalidate it.

## What the accuracy numbers mean

- **Task pass rate:** task/trials passing every visible and withheld case in both
  runtimes divided by every admitted task/trial in that arm. Failed or unrun trials
  remain in the denominator. These are algorithm-task results, not method counts.
- **Case parity:** passed / planned cases, separately for visible and withheld
  splits and CPython/GraalPy. Unvalidated cases receive no operational accuracy
  credit and are also counted separately. An integrity-invalid run receives no
  accuracy credit, though its raw observations remain available.
- **Paired change:** repaired minus initial task success and withheld case parity
  in percentage points, for the same task/trial.
- **Effort:** attempts, code/environment repairs, input/output tokens, model calls,
  usage-unknown calls, and elapsed time. The initial generation cost is counted
  once under one-shot; repair arms report incremental calls.

Wilson intervals are descriptive across the admitted task/trials. Cases, runtimes,
and methods within a library are correlated; neither those intervals nor a small
pilot establishes generalization to repositories. No improvement is a valid result.

Recompute the report from raw artifacts:

```sh
python3.12 -m migration_lab report runs/EXPERIMENT_DIRECTORY
```

## Bounded agent behavior

The controller records preflight, reference, translation/code repair, visible
execution, checkpoint selection, and final scoring. The Environment Agent can
recognize a denied GraalPy cache write in a trusted probe, switch to the approved
writable ephemeral cache, then repeat the probe. That action consumes one of the
same five repair rounds available to the Migration Agent. Unknown failures stop;
the system does not invent commands, install dependencies, change expected answers,
or weaken isolation. This is a small deterministic remediation policy, not a
fully general environment-planning LLM.

Test that policy separately with a controlled fault:

```sh
python3.12 -m migration_lab experiment \
  --suite evaluator-private/pilot-v1.json --backend replay \
  --replay-manifest fixtures/replay.json --task levenshtein --trials 1 \
  --fault graal-cache --archive
```

Both repair arms receive the same cache-path fault; the one-shot anchor uses the
healthy environment. The fixed-environment arm must retain the setup failure.
The environment arm may repair the cache configuration, then use the remaining
code-repair budget. Keep these results separate from natural translation accuracy.
Synthetic replay does not establish live-model repair effectiveness.

## Execution boundary and limits

Candidate images contain a runner and runtime dependencies only. In particular,
the GraalPy image contains a guest-only harness with no Java reference algorithms.
Images use pinned base digests; the local lock records built image IDs, input and
dependency hashes, OS, and architecture. Changing image inputs requires a rebuild.
Build contexts are assembled from an explicit file list, never the whole repo.

Containers use no network, an unprivileged UID, read-only root and candidate,
no added capabilities, no privilege escalation, one CPU, 128 processes, bounded
memory/swap, bounded temporary storage, and no Docker socket or host-home mount.
CPython receives 256 MiB memory and 64 MiB scratch; GraalPy receives 1536 MiB and
512 MiB. GraalPy's scratch allows native library loading; guest filesystem/host
access remains disabled. Source/tests/comparator and reference answers stay outside
candidate mounts. Only case inputs for the current execution arrive on stdin.

Output capture is bounded while streaming, stopping at 2 MB per stream; it no
longer writes an unbounded temporary output file. Timeouts and cleanup remove the
whole container, including descendants. Missing images/daemon fail closed.
Container isolation reduces host exposure; it is not a proof against kernel or
runtime vulnerabilities, and an in-process language runner is not a proof against
all deliberate protocol forgery. Evaluations measure behavioral parity on fixed
inputs, not adversarial equivalence.

The loop wall-time budget is still checked between operations. Preflight, final
scoring, and Docker cleanup can extend total elapsed time. Per-process timeouts
and container limits are enforced independently. Automatic runtime repair is
currently limited to preflight cache configuration; mid-run infrastructure routing,
broader environment actions, and resumable interrupted batches remain future work.

Implementation references: [Docker run controls](https://docs.docker.com/reference/cli/docker/container/run/)
and [Responses structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

## Commons CLI milestone: stateful qualification

The next slice is now implemented: Commons CLI **1.9.0**, pinned from its Maven
source artifact with per-file hashes, through `Option`, `Options`, `DefaultParser`,
and `CommandLine`. This is a new benchmark version, **not an AlphaTrans-matched
comparison**. The exact constructors, methods, types, and scope exclusions live in
`benchmarks/commons_cli.json`.

The evaluator owns a typed operation sequence. It constructs objects, preserves
handles, calls only declared methods, and records a snapshot after each operation.
The Java oracle uses explicit dispatch into the unmodified pinned library. CPython
and GraalPy use the same Python adapter. Comparisons require exact typed values,
ordered lists, canonical object aliases, and exception types; exception messages
are excluded. Sequences stop at the first exception. Repair feedback reports the
first differing operation, which is an observable mismatch, not source-line fault
localization. Missing API classes and malformed or truncated traces fail validation.

There are 20 visible scenarios and 60 holdout sequences. Scenarios cover option
metadata, aliases, short/long arguments, repeated values, Unicode values, missing
arguments, unknown options, required options, stop behavior, and parser reuse.
The holdout uses new names/values across the same 20 templates: it checks parameter
variation, **not independent semantic generalization**. These are project-authored
scenarios; Commons CLI upstream JUnit reuse is not yet implemented.

From `midpoint/`, qualify the integration without model calls:

```sh
python3 scripts/bootstrap.py
python3 -m unittest discover -s tests -v
python3 scripts/verify_cli.py --archive
```

The qualification script freezes repeated Java observations, runs the deliberately
broken state-reuse fixture, then replays the hand-written corrected fixture through
the existing bounded repair controller. It checks both CPython and GraalPy, selects
using visible results only, and scores holdout after selection. Its artifacts are
labelled `synthetic_fixture`. The result is harness qualification, never LLM accuracy.
Local subprocess execution here is for these trusted fixtures only.

To prepare a fresh experiment protocol and run the existing three paired arms:

```sh
python3 -m migration_lab freeze --task commons_cli \
  --output evaluator-private/commons-cli-v1.json
python3 scripts/build_containers.py
python3 -m migration_lab experiment --task commons_cli \
  --suite evaluator-private/commons-cli-v1.json --backend replay \
  --replay-manifest fixtures/replay.json --trials 1 --archive
```

This last command still uses synthetic replay. Live backend experiments require
explicit model configuration, budgets, and working containers as documented above.
Changed runner inputs require rebuilding images. The new images include only the
trusted dispatch modules, contract metadata, and runtime dependencies; they contain
no Commons CLI implementation or reference outputs. Docker was unavailable for the
local milestone verification, so the updated images still need build/runtime tests.
Existing `all` defaults for demos/freezing retain the three string tasks; select
`commons_cli` explicitly. Experiment `--task all` uses the tasks in its frozen suite.
Schema-2 suites bind the CLI source, contract, adapters, and generator fingerprints;
source/runner/comparator changes require a fresh suite. Historical evidence remains
historical evidence and must not be relabelled as results from the new protocol.

Remaining research work: expand independent semantic tests and negative fixtures;
run live paired trials; add source-guided test construction and counterexample
minimization; then introduce dependency-ordered multi-module translation. Current
context uses a conservative, manually pinned source-name closure, not a general
symbol resolver. The candidate is still one module. Whole-repository migration,
formal equivalence, general environment planning, and a measured gain over a fixed
LLM baseline are not claimed by this milestone.

## Diagnosing Gemini before a benchmark

`experiment --model-timeout 120` now controls the model HTTP socket timeout
separately from `--timeout`, which controls candidate execution. The actual model
request timeout is capped by the remaining loop deadline and recorded in run
metadata. This is a socket timeout, not a strict end-to-end cancellation guarantee.
Gemini transport errors record whether the client was awaiting response headers
or reading the response body, plus the configured timeout and elapsed time.

Run `python3 scripts/diagnose_gemini.py` from `midpoint/` for one tiny curl
request with DNS/connect/TLS/first-byte timings. It reads `GEMINI_API_KEY` from
the environment or ignored `.env`, sends no repository code, never executes
returned code, and reserves at most $0.02 at the currently configured rates.
It stores sanitized diagnostics under `runs/`. A successful metadata GET alone
does not demonstrate that generation works. HTTP 503 or generation timeouts
should be investigated before launching another benchmark batch.

On this Mac, Python 3.15 has no default CA file. For Python API commands, use
`SSL_CERT_FILE=/etc/ssl/cert.pem` with this existing system CA bundle, or configure
a valid CA bundle for your Python installation. Never disable TLS verification.
The diagnostic curl command uses its own verified system trust configuration.

### Completed Commons CLI live configuration (November 17)

The successful batch used `--backend gemini --model gemini-3.8-flash
--reasoning-effort low --task commons_cli --trials 3 --max-repairs 5
--model-timeout 300 --timeout 90 --max-output-tokens 32768
--output-token-budget 196608 --max-spend-usd 1
--input-usd-per-million .75 --output-usd-per-million 3.75 --archive` with the
previously frozen CLI suite. These settings differ from the earlier failed
medium-thinking requests; report the configuration when comparing results.
The experiment CLI exits 1 when any admitted arm fails validation, including
an intentionally retained unsuccessful one-shot baseline. Check `summary.json`
and per-arm statuses to distinguish completed negative results from setup errors.
See [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md#november-17-2026--live-commons-cli-results).

## Semantic v2 and feedback-ablation commands

From `midpoint/`, freeze the stronger task profile before model generation:

```sh
python3 -m migration_lab freeze --task commons_cli \
  --profile commons-cli-semantic-v2 --seed 6158 \
  --output evaluator-private/commons-cli-semantic-v2.json
```

The profile's generator is fingerprinted, and its oracle is repeated before
freezing. Default pilot behavior is retained. Changing the profile or protocol
requires a newly frozen suite; archived historical evidence remains historical.
The semantic profile is never included in source-context assembly.

`python3 scripts/qualify_cli_semantics.py --suite <suite.json> --baseline <candidate.py>`
evaluates an existing candidate and eight synthetic mutations in Docker. It counts
new failures relative to that baseline, reports execution errors separately, uses
visible cases only, and archives its evidence. Baseline correctness is measured
against Java; it is never assumed merely because a previous suite passed.

Add `--feedback-ablation` to the existing `experiment --backend gemini --task
commons_cli` command to select `one_shot`, `basic_feedback`, and
`operation_feedback` arms. Default experiments retain the original repair arms.
Both feedback arms share the initial candidate, model settings, per-call limits,
repair limits and no-regression selection. Repair order alternates by trial.
Each independent trial starts fresh; repair feedback is reused only within that
trial. No generated candidate is manually edited by the researcher.

The shared spend cap can still prevent a later arm from making its permitted
calls. The November 17 study encountered this in trial 5. Reports now expose
`repair_budget_blocked` and count only evaluated repair candidates in
`code_repairs`; `repair_attempts` retains all scheduled attempts. Do not interpret
a budget-blocked arm as evidence against its feedback treatment. Reserve equal
per-arm capacity in the next study before making a comparative claim.
# Fair-budget main-study preparation

New experiments default to `--budget-policy partitioned`: the declared spend cap must cover independent worst-case initial and repair allocations before any API request. An insufficient cap fails upfront; it is never raised automatically. Use `--budget-policy shared` only when intentionally reproducing the historical shared-budget protocol. See [BUDGET_SCOPE_OBSERVATIONS.md](BUDGET_SCOPE_OBSERVATIONS.md) for the reservation calculation, scope audit, validation, and remaining main-study gaps.

## CLI v3 and retry-memory experiments

See [RETRY_MEMORY_OBSERVATIONS.md](RETRY_MEMORY_OBSERVATIONS.md) for implementation details and limitations. The new contract requires a new frozen suite and rebuilt Java/Docker harnesses; old archives remain historical evidence, not compatible suites for the changed evaluator.

From `midpoint/`, freeze the evaluator before generation:

```sh
python3 -m migration_lab freeze --task commons_cli \
  --profile commons-cli-extended-v3 --seed 6158 --output runs/cli-v3/suite.json
```

Add `--retry-memory` to enable pruned feedback and arm-local history in the main study, or `--memory-ablation` for the separate one-shot/memory-off/memory-on comparison. The latter keeps the current feedback format identical and changes only accumulated history. Do not combine either with `--feedback-ablation`. Use `--max-repairs 3` for the planned initial comparison. Partitioned budget preflight still applies.

A no-API integration check is available:

```sh
python3 scripts/prepare_cli_v3_replay.py --output runs/cli-v3-fixtures
python3 -m migration_lab experiment --backend replay \
  --replay-manifest runs/cli-v3-fixtures/replay.json \
  --suite runs/cli-v3/suite.json --task commons_cli --trials 1 \
  --max-repairs 3 --timeout 90 --memory-ablation --archive
```

The prepared responses are synthetic fixtures, explicitly including hand-written additions and injected faults. Replay accuracy is not live model performance. Each attempt produces a dependency report and requirements file; no third-party distributions are approved for this standard-library-only task.


## Staged live CLI v3 study runner

`scripts/run_cli_v3_study.py` runs one explicitly selected phase: `--phase smoke`, `--phase main`, or `--phase memory`, with `--suite` pointing to a frozen v3 suite. It reads the local Gemini key without printing it, requires Docker, and archives failures as well as successes. Defaults are the predeclared three-trial protocol in [CLI_V3_LIVE_OBSERVATIONS.md](CLI_V3_LIVE_OBSERVATIONS.md), including a $0.40 smoke cap and separate $8 caps for each study. Invoking a phase makes live API calls; it is not a replay command. The completed study's results and remaining limitations are recorded in that document.
