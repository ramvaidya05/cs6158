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

Live batches now use an availability guard: three consecutive timeout, transport,
rate-limit, or HTTP 5xx failures open a circuit and stop further requests.
Authentication, access, quota, dollar-budget, or model-identity failures stop
immediately. Successful responses reset the consecutive-failure count; invalid
generated code does not trip this provider-availability rule. Remaining admitted
arms keep `not_run` results with an explicit reason, and `provider-stop.json`
records the trigger. Already selected candidates are still scored after selection
freezes. The guard never retries, changes models, or modifies evaluator settings.

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
schema response. It reads `GEMINI_API_KEY` or the ignored owner-only `.env.gemini`
created by `python3.12 scripts/configure_key.py --provider gemini`.
For a memory-only key, use `scripts/live_pilot.py --backend gemini`; its prompt
disables terminal echo. Never put the key directly in a shell command.
`--reasoning-effort` maps to
Gemini's thinking level. Thinking tokens count toward `--max-output-tokens`,
so allow more headroom than for OpenAI. Prices are always explicit; on the
free tier, pass the paid list rates so the budget still caps spend if billing
is enabled.

```sh
python3.12 scripts/live_pilot.py \
  --suite evaluator-private/pilot-v1.json --backend gemini \
  --model gemini-3.8-flash --reasoning-effort medium \
  --input-usd-per-million 0.75 --output-usd-per-million 3.75 \
  --task levenshtein --trials 3 --max-repairs 5 \
  --max-output-tokens 16384 --output-token-budget 98304 \
  --max-spend-usd 1
```

Gemini 3.8 Flash prices ($0.75/M input, $3.75/M output through December 31,
2026) and free-tier availability were checked against the official pricing page
on October 19, 2026. Do not edit files under `migration_lab/`, `tests/`,
`scripts/` or other protected folders while a run is in progress; the integrity
guard will invalidate it.

### Fixed expansion protocol (November 11, 2026)

The next natural study admits three trials of each of the three algorithms,
using `--task all --trials 3`, the existing frozen suite, Gemini 3.8 Flash with
medium thinking, 16384 maximum output tokens per call, and 98304 reserved output
tokens per arm. The entire natural batch has a $0.65 reservation cap. A separate
controlled cache-fault study admits one trial of each algorithm with the same
model/configuration, `--fault graal-cache --task all --trials 1`, and a $0.25 cap.
Neither study extends its trial count in response to observed successes or
failures. Both reuse byte-identical initial translations within paired arms.
The frozen pilot suite is now an exposed evaluation set, not a fresh blind holdout.

The cache-fault study tests bounded autonomous recovery using live translations.
Its deliberately broken fixed-environment arm measures operational failure;
it must not be interpreted as inferior translation semantics. It is reported
separately from natural translation results.

The natural batch encountered provider timeouts/HTTP 503 and exhausted its
reservation budget without generating a candidate. The fresh-model fault batch
was consequently deferred. A separate, explicitly labeled recorded-response
study uses the unchanged candidate from trial 0 of the October Gemini archive;
its copied original response/prompt and hashes preserve provenance. This is an
environment-recovery check, not an additional independent translation trial.

### Follow-up protocol (November 13, 2026)

Admit three trials each of `normalized` and `jaro_winkler` before generation,
using `scripts/live_pilot.py --tasks normalized jaro_winkler --trials 3`.
Keep Gemini 3.8 Flash, medium thinking, the original frozen suite, 16384 output
tokens per call, and 98304 reserved output tokens per arm. The batch reserves
at most $0.20, within the remaining $1 Gemini allowance after all earlier Gemini
attempts (including the integrity-invalid run and unknown-usage failures).
The provider-availability guard is active. No extra trials are added based on
success or failure; remaining admitted trials stay recorded if the budget or
availability policy stops the batch.

After that batch's two timeouts and budget stop, the user authorized an additional
$1 reservation for a new batch of the same six task/trials. Its model, thinking,
token limits, frozen suite, and provider-failure policy are unchanged. The two
batches remain separate records; new attempts do not replace earlier failures.

## Inspect archived results without changing them

`report` prints recomputed results without rewriting the archived `summary.json`.
For an archive with `checksums.json`, it first verifies the complete file inventory
and every recorded checksum. `catalog` verifies multiple experiment archives,
rejects duplicate content, and keeps each batch's accuracy separate:

```sh
python3.12 -m migration_lab catalog evidence/*-experiment-* \
  --output reports/experiment-history.md
```

Include separately named recorded-response experiment directories explicitly when
needed. Catalog output must be outside the input archives and must be a new file.
Use `--format json` for the complete per-task results and experiment accounting.
The index includes failed and integrity-invalid experiments, flags uncompleted
trials, and does not pool model accuracies. Standalone adapter diagnostics are
outside its experiment accounting; conservative reservations are not measured
provider charges. Checksums detect changes relative to the saved manifest; they
do not prove independent authenticity of an archive.

## Check evaluator sensitivity with synthetic faults

```sh
python3.12 scripts/verify_semantics.py --suite evaluator-private/pilot-v1.json
```

This freezes seven explicit source-semantic mutations of the hand-authored
fixtures before execution, verifies the correct fixtures as controls, and scores
every mutation in both containers. It archives the mutation definitions,
candidate hashes, frozen inputs, runtime outputs, and per-split mismatch counts.
A runtime failure is not credited as a semantic detection. Surviving mutations
remain recorded; the command does not alter tests or start a model repair loop.
This measures sensitivity to selected faults, never LLM accuracy. In the first
run, fractional JaroWinkler transpositions escaped all visible cases but failed
30 withheld cases per runtime. Keep that limitation separate from code-repair
effectiveness and do not feed those withheld failures into the current protocol.

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

`summary.json` also reports `by_task`, completion counts, pass rates among
completed task/trials, and `repair_opportunities`. A repair opportunity requires
an evaluated initial translation with visible failures; a transport/setup failure
is not a code-repair opportunity. Paired deltas retain the operational denominator
and flag whether both arms completed. Full recovery counts require both a repair
opportunity and a final pass on all visible/withheld cases in both runtimes.
Zero opportunities provides no evidence of code-repair effectiveness.

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
