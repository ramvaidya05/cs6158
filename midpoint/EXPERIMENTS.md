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
