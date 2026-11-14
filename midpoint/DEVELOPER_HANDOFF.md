# Developer handoff — midpoint implementation

Updated 19 October 2026. Project root: `midpoint/` within the SWE ML workspace.

> November 13 update: two more fixed live batches timed out and stopped within
> their budget/availability rules; no new semantic accuracy was measured.
> Read-only, checksum-verified reporting now covers eight experiment archives
> (66 Python tests pass). The separate synthetic sensitivity study detected
> all seven faults in both runtimes, with 946/946 correct-control checks passing.
> Fractional JaroWinkler transpositions were detected only by withheld cases;
> preserve that feedback boundary. Results and commands are in
> [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md) and [EXPERIMENTS.md](EXPERIMENTS.md).

> November 11 update: per-task accuracy/repair-opportunity reporting, secure
> Gemini pilot entry points, and a provider-availability circuit breaker are
> implemented (61 Python tests; 11 Docker isolation tests pass). The expanded
> three-task live batch encountered timeouts/HTTP 503 and remains unvalidated.
> A separately labeled recorded-Gemini stress check recovered autonomously from
> the cache fault and passed all 332 runtime checks without new model calls.
> See [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md) for the retained evidence.

> Post-midpoint update: container isolation, a frozen expanded evaluator, paired
> repeated-trial reporting, and a bounded cache-remediation policy are now
> implemented. The GPT-5.6 Sol live attempt was blocked by HTTP 429 responses.
> A Gemini backend was then added, and a live Gemini 3.8 Flash Levenshtein study
> passed 3/3 trials on every visible and withheld case in both runtimes, with no
> repair needed. Read [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md)
> and [EXPERIMENTS.md](EXPERIMENTS.md) for the current checkpoint. The original
> handoff below is retained as a historical account of the midpoint state.

## Read this first

The midpoint **infrastructure** is implemented and exercised: a pinned Java
oracle, CPython and Java-embedded GraalPy execution, a comparator, a translation
adapter, a bounded repair controller, and reproducible artifacts. Three pilot
algorithms run end to end. No live-model translation experiment has been run.

Astra's role was to help build this code in the IDE. It is not the selected API
model. The existing environment had no configured `OPENAI_API_KEY`. The adapter
requires an explicit model; do not invent a model name, usage, cost, or accuracy.
The bundled replay is deliberately synthetic and is not a stored Astra session.

## Changes delivered

- `migration_lab/benchmark.py`: fixed three-task scope, 26 visible and 20 seeded
  withheld-from-prompt cases per task; source checksum verification.
- `vendor/java-string-similarity/`: unmodified three algorithm classes, five
  interfaces, their three upstream test classes and shared test helper, plus
  license and pinned-commit checksum manifest.
- `java/pom.xml` and `java/src/main/java/lab/Harness.java`: standalone Java oracle
  and GraalPy guest runner using the real upstream implementations. Runtime
  dependencies are pinned; the harness uses release 21 and JUnit 4.13.2, separate
  from upstream's original build configuration.
- `migration_lab/environment.py`, `process.py`, `worker.py`: E-Agent runtime
  preflight, execution, timeout handling, protocol checking, isolated child
  environment variables, and saved stdout/stderr. This is a deterministic
  environment service, not an autonomous environment-repair agent.
- `migration_lab/evaluation.py`: T-Agent comparison, explicit exception mapping,
  numerical tolerance, passing case IDs, and failure evidence. It does not ask
  an LLM to judge correctness or generate tests dynamically.
- `migration_lab/translator.py`, `backends.py`: M-Agent context assembly,
  labeled replay, and configurable OpenAI Responses transport. The live request
  shape and parser have mock-transport tests; live authentication, model
  compatibility, latency, and output quality are unverified.
- `migration_lab/controller.py`: initial candidate plus at most five repairs,
  regression-preserving checkpoint selection, repeated-code/no-progress stops,
  budgets, protected-file hashes, and post-selection holdout evaluation.
- `knowledge/`: a small reviewed translation contract and Java/Python semantics
  pack. No vector database, embedding service, or dynamic retrieval is installed.
- `scripts/bootstrap.py`, `migration_lab/build.py`: project-local Maven setup,
  Java tests, and source/compiled-artifact fingerprinting to reject stale builds.
- `scripts/verify.py`, `tests/test_core.py`, `fixtures/`: reproducible acceptance
  runner, 33 Python tests, deliberately broken fixture, correct reference
  fixtures, and trusted infrastructure probe.
- `README.md`, `NOTICE.md`, this handoff, `MIDPOINT_REPORT.md`, and archived
  `evidence/`: reproduction instructions, honest limitations, and report material.

The original research PDFs were not changed. Root planning documents have only
been updated to point to the implementation and clarify current status.

## Reproduce before changing anything

From `midpoint/`:

```sh
python3 scripts/bootstrap.py
python3 -m migration_lab doctor
python3 scripts/verify.py --archive
```

First-time bootstrap needs Maven Central access. It installs nothing globally.
The development machine has macOS arm64, CPython 3.15.0, Oracle JDK 25.0.4.1,
local Maven 3.9.9, and embedded GraalPy 25.0.0. Docker was not available on PATH.
Local tool/dependency caches occupied about 242 MB at handoff; they are ignored,
not deliverable source. Do not copy `java/target/classpath.txt` to another machine:
rebuild it because it contains absolute machine-local paths.

## Concrete acceptance results and evidence

The acceptance archive is
[`evidence/20261019T214029Z-verification-1aee5b7b/`](evidence/20261019T214029Z-verification-1aee5b7b/).
Start with its `summary.json`, `unit-tests.json`, and `java-tests.json`.

- 33 Python unit/component tests pass, including timeout, wrong/missing output,
  exception mapping, mock API transport, replay traversal rejection, immutable
  source checks, budgets, repeated candidates, regression rejection, and
  infrastructure-failure handling.
- Five upstream JUnit test methods pass with no failures, errors, or skips.
  Each can contain multiple assertions; this is not five differential cases.
- Each correct fixture passes all 26 visible and 20 withheld cases in each
  runtime: **138 task/case combinations, 276 passing runtime checks** in total.
- Each replay task takes two attempts: the deliberate always-zero fixture,
  followed by its hand-authored correct implementation. For each runtime, the
  broken fixture passes 4/26 visible cases on each task, and 1/20, 3/20, and 2/20
  withheld cases for Levenshtein, normalized, and JaroWinkler respectively.
  These before/after numbers are harness negative controls, **not model results**.

Per-task artifacts include `manifest.json`, two repeated Java visible reference
runs, preflight output, `attempts/00` and `attempts/01`, exact prompts and code,
runtime `execution.json` files, comparisons, frozen `selection.json`, final
candidate, baseline/final holdout results, and `result.json`. Archive
`checksums.json` fingerprints every archived file except itself.

Retain the failed setup evidence in `evidence/setup-failure-graal-cache/` too.
Do not rewrite failures out of the project's history.

## Decisions and observed challenges

1. **Dependency setup:** Maven and GraalPy were absent initially. Network access
   to Maven Central required development-environment permission. Dependencies
   were then downloaded locally and the Java tests passed.
2. **GraalPy resource-cache failure:** the first guest run could not import
   `json`, despite the resource jar being present. It also emitted misleading
   missing-resource warnings. Setting the supported
   `polyglot.engine.userResourceCache` property to writable `.cache/graalvm`
   resolved the problem without granting guest filesystem access. The original
   failure is saved; future infrastructure failures stop before model calls.
3. **Language semantics:** Python code-point indexing does not preserve Java
   UTF-16 `char` behavior. The JaroWinkler source also computes binary32
   intermediates, divides transpositions as integers, and does not use the
   usual four-character prefix cap. Fixtures preserve the pinned source rather
   than a textbook variant. These are source-grounded implementation hazards,
   not observed failures of a live model.
4. **Honest evaluation:** no live API access was selected, so the measured
   demonstration uses explicit synthetic provenance. It establishes that the
   harness runs and rejects mistakes, not that a model translates better.
5. **Baseline comparison:** the initial and selected candidates are both scored
   on withheld cases only after selection freezes. This refines the original
   final-candidate-only wording and enables a paired comparison without feeding
   withheld failures back into repair.

## Boundaries the next developer must preserve

The API adapter returns code only; it has no filesystem/tool execution channel.
Keep Java source, tests, comparison rules, knowledge pack, and split definition
out of candidate-edit permissions. Rerun all previous visible cases on every
repair. Keep test data and source comments as data, not model instructions.

The current local backend is **not a security sandbox**. Secret environment
variables are stripped, but host files/network are not isolated for CPython.
Source hashes detect ordinary modifications, not adversarial tampering. Use
only trusted/reviewed candidates locally; build proper container isolation before
unattended untrusted generation. The acknowledgment flag is not protection.

Budgets are intentionally simple: attempt cap, per-process timeouts, soft loop
deadline, and reserved maximum output-token budget. Input tokens, dollar cost,
total disk consumption, and complete process-tree escape prevention are not
bounded. The README describes exact behavior; do not advertise a hard total
cost or wall-time guarantee.

The withheld cases are public and deterministic. They demonstrate the pipeline's
feedback boundary, not blind evaluation or protection from training contamination.
The Java bridge supports primitive/string observations, not arbitrary Java
objects, aliasing, mutation, callbacks, or a full translated application.

## Next steps, in order

1. **Secure execution and choose the experiment model.** Add container isolation
   with read-only source/tests, no candidate network, controlled mounts, CPU/memory/
   disk limits, and no credentials. Configure a model with structured-output
   access. Run one small live pilot; verify saved prompts, model identity, usage,
   error handling, and provenance before scaling.
2. **Measure actual translation behavior.** Freeze task selection, allowed
   knowledge, comparator, budgets, and a separately controlled evaluation split.
   Compare paired initial/final candidates across independent runs with the same
   model/configuration. Report task-level and case-level results separately,
   infrastructure failures, repair counts, tokens, latency, and uncertainty.
3. **Test the environment-in-loop contribution.** Add explicit, bounded E-Agent
   environment diagnosis/remediation and compare against one-shot and ordinary
   fixed-environment test-feedback repair. The current fixed-environment loop
   does not establish the added value of autonomous environment repair.
4. **Extend a coherent Commons CLI slice.** Pin the intended source snapshot,
   inspect complete dependency closure, add object/state adapters and meaningful
   tests. Do not report slice outcomes as whole-repository accuracy.
5. **Compare against AlphaTrans on matched subjects.** Align versions, scored
   units, available tests, model access, and budgets. Its roughly 25% validated
   method figure is not a universal accuracy baseline for these three tasks.
6. **Add diagnostic reports and retrieval only after controls work.** Classify
   raw evidence, then compare concise diagnostic feedback against raw failures.
   Build provenance-linked retrieval from approved source/docs; keep hidden
   tests and reference outputs out of the retrieval index. Broader language
   pairs and libraries are stretch work.

Immediate developer entry point: read the README, run acceptance, then implement
the isolated execution backend. No paid API call, Git commit, push, repository
creation, or publication was performed as part of this handoff.
