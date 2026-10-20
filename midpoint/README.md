# Environment-in-the-Loop Translation — midpoint prototype

A small, executable Java-to-Python translation/repair research harness. It has
separate Migration, Environment, and Testsuite roles, coordinated by a bounded
controller. Only Migration uses a model; Environment and Testsuite are deterministic.

**Current status:** disposable container execution, frozen evaluation sets, paired
trial aggregation, and a bounded cache-remediation policy are implemented. The
expanded fixture check passes 946 runtime checks. A live Levenshtein study with
Gemini 3.8 Flash (free tier) passed 3/3 trials: every one-shot translation matched
all 26 visible and 140 withheld cases in both CPython and GraalPy, so no repair was
needed. An earlier GPT-5.6 Sol attempt returned HTTP 429 and remains unvalidated.
See [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md) for the numbers and [EXPERIMENTS.md](EXPERIMENTS.md) for the current workflow.
The original midpoint replay and its evidence remain below for reproduction.

Start with [DEVELOPER_HANDOFF.md](DEVELOPER_HANDOFF.md) for changes, evidence, and
the post-midpoint work queue. See [MIDPOINT_REPORT.md](MIDPOINT_REPORT.md) for a
report draft grounded in the implementation.

## Run locally

Prerequisites: Python 3.12+ and JDK 21+ on PATH. On the current Mac use
`/opt/homebrew/bin/python3.12`; plain `python3` resolves to unsupported 3.9.
The current host is macOS arm64 with CPython 3.12.14 and Temurin JDK 25.0.1.
Historical midpoint evidence used CPython 3.15.0 and Oracle JDK 25.0.4.1. GraalPy embedding dependencies are pinned
to 25.0.0; no standalone `graalpy` or GraalVM JDK installation is required for
this tested configuration. Other OS/JDK combinations remain untested.

From this directory:

```sh
python3 scripts/bootstrap.py
python3 -m migration_lab doctor
python3 -m unittest discover -s tests -v
python3 -m migration_lab demo
```

Bootstrap downloads Maven 3.9.9 locally if no Maven is available, verifies its
published SHA-512, downloads the pinned Java dependencies, builds the harness,
runs the selected upstream tests, and records a build fingerprint. All caches
stay in `.tools/`, `.cache/`, and `java/target/`; it does not install global tools.
The first bootstrap needs network access and appreciable disk space for GraalPy.
Python execution uses the standard library only; no pip installation is needed.

The one-command acceptance suite records unit-test output, upstream JUnit XML,
Java reference outputs, prompts, candidate code, runtime output, and comparisons:

```sh
python3 scripts/verify.py --archive
```

This writes a new immutable-by-convention timestamped copy under `evidence/`.
Ordinary development runs go under ignored `runs/`. Do not edit an old run to
make it pass; make a new run. `checksums.json` detects subsequent archive changes.

## What is being tested?

Three dependency-closed tasks from pinned `tdebatty/java-string-similarity`:
Levenshtein, NormalizedLevenshtein, and JaroWinkler. The commit and unmodified
source/test checksums are in `vendor/java-string-similarity/SOURCE.json`.

The original demo has 26 visible cases and 20 withheld-from-prompt cases per task.
The expanded frozen suite is described in [EXPERIMENTS.md](EXPERIMENTS.md). Original Java
produces expected outputs; the same candidate is evaluated in CPython and in
GraalPy embedded inside the Java harness. The 138 task/case combinations become
276 runtime checks, **not 276 independent inputs or 138 translated methods**.
Upstream JUnit tests validate the Java oracle only; they have not been rewritten
to call Python. The bridge performs differential JSON primitive/string checks,
not arbitrary Java-object conversion or state synchronization.

Cases cover empty/equal strings, nulls, repeated characters, supplementary
Unicode, limit boundaries, similarity operations, and seeded generated inputs.
Java `NullPointerException` maps explicitly to Python `ValueError`; messages are
recorded but not scored. Finite numeric values use relative/absolute tolerance
`1e-9`. Zero-test runs, booleans as numbers, missing rows, and runtime failures
cannot pass.

## Agent/controller behavior

`MigrationAgent` receives pinned Java source, its interfaces, and the two small
reviewed files in `knowledge/`. Repair prompts additionally receive the selected
candidate and up to six visible failures per runtime. The model never decides
whether its output passed.

The controller evaluates one initial candidate, then at most five repairs. It
keeps a better checkpoint only if no previously passing visible case is lost
in either runtime. It stops on full visible success, repeated code, two rounds
without progress, the attempt limit, or a configured budget. Syntax errors,
execution failures, timeouts, and mismatches are separately recorded. A trusted
preflight probe checks both runtimes before asking for a translation.

Selection is frozen before evaluating withheld cases. **Both the initial and
selected candidates** are scored on that same split after the loop, to support
a paired baseline comparison. Neither score goes back into the repair prompt.
This slightly refines the earlier plan, which mentioned scoring only the final
candidate. The public seeded demo split is not a private or contamination-proof
research holdout.

The bundled replay intentionally returns an always-zero implementation, then a
hand-authored correct fixture. It proves orchestration and error detection only.
Its pass-rate increase must never be described as an LLM improvement.

## Run a live model experiment

GPT-5.6 Sol was selected for the pilot; the IDE assistant is not experimental
evidence. Configure
`OPENAI_API_KEY` in the shell using your normal secret-management workflow;
do not paste credentials into source, the report, or chat.

```sh
python3.12 scripts/build_containers.py
python3.12 -m migration_lab freeze --output evaluator-private/pilot-v1.json
python3.12 -m migration_lab experiment --backend openai \
  --model gpt-5.6-sol --task levenshtein --trials 3 \
  --suite evaluator-private/pilot-v1.json --max-spend-usd 1 --archive
```

The adapter uses the OpenAI Responses API with a strict JSON schema containing
`code` and `explanation`, saves the returned model identity and usage, and has
no model default. The model must support that API and structured output. Add
`--reasoning-effort` only if that model supports it. A `--max-repairs 0` run is
one-shot; an iterative run's initial candidate is also a paired one-shot baseline.

Default controller limits per arm: six maximum calls, 8,192 requested output tokens/call,
49,152 reserved output tokens, 900-second loop budget, and 60 seconds per child
process. The token budget reserves requested maxima; it is **not a total-token
or dollar cap**. Input tokens still cost money. The loop deadline is checked
between attempts; active evaluations and final holdout scoring can extend beyond
it. Failed API calls are not retried invisibly. Actual returned usage is saved.

For your own previously recorded responses:

```sh
python3 -m migration_lab run --backend replay \
  --replay-manifest /absolute/path/to/replay.json \
  --task levenshtein --execution container
```

Use the manifest structure in `fixtures/replay.json`, with provenance
`saved_model_response` for genuine saved model outputs. Supply source filenames
relative to the manifest directory and keep original model/prompt/run provenance
alongside them. Replay is still not fresh inference.

## Safety and research limitations

- **Local subprocesses are not an OS security sandbox.** Only execute trusted,
  reviewed code on this backend. The acknowledgment flag does not add isolation.
  Live code now requires the container backend; there is no fallback to local
  execution. Local replay still exposes host files/network. Output capture stops
  at 2 MB per stream; other local process resources remain unbounded.
- GraalPy disables guest filesystem/network IO, host lookup, and thread creation.
  Those restrictions and source hashes do not make CPython safe against hostile
  code or prove absence of evaluator tampering. Hash checks detect ordinary edits;
  they are not a security boundary. No privileged host tools are exposed to the model.
- Existing source, tests, comparator, context pack, and fixtures are hashed in
  each run. Compiled Java is bound to source/POM inputs and checked for stale or
  changed artifacts. Dependency jars are pinned by Maven coordinates, not a
  complete independently verified supply-chain lockfile. The container image lock
  additionally fingerprints the exact dependency jar bytes used to build the images.
- The context pack is static, source-grounded assistance, not vector RAG. Its
  UTF-16 and binary32 notes are allowed knowledge, not hidden answers. Performance
  comparisons must give equivalent context to baseline and repair conditions.
- Three familiar algorithms and a public generated split cannot establish
  generalization, lack of training contamination, or superiority over AlphaTrans.
  The bounded cache-remediation policy is implemented; an object bridge, Commons
  CLI slice, and general environment-planning agent remain future work.

## Troubleshooting

- Missing/stale harness: run `python3 scripts/bootstrap.py` again. Do not hand-edit
  `java/target/classpath.txt` or `build.json`.
- Maven Central DNS/access failure: allow the bootstrap dependency download in
  your development environment, then rerun. No global Maven installation is needed.
- GraalPy cannot import `json`: inspect the saved execution stderr. This project
  sets `polyglot.engine.userResourceCache` to the writable project-local cache;
  verify that `.cache/graalvm` is writable. The initial failure and resolution
  are described in the handoff.
- A run returning exit code 1 completed but did not fully validate; exit code 2
  signals configuration/execution failure. Inspect task `result.json` and the
  relevant `execution.json`; never convert an infrastructure failure to a pass.

References: [GraalVM embedding and resource-cache documentation](https://www.graalvm.org/latest/reference-manual/embed-languages/),
[Responses API structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
and [upstream library](https://github.com/tdebatty/java-string-similarity).
Third-party notices are in [NOTICE.md](NOTICE.md).
