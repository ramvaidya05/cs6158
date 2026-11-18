# Current checkpoint — November 17, 2026

## CLI v3 live Gemini studies — November 17, 2026 local time

Fresh live runs now evaluate the expanded 32-method CLI scope. Main study: one-shot, code repair, and environment-aware repair each passed 3/3 trials; all initial translations passed, so no repairs occurred. Separate memory cohort: one-shot passed the full visible-and-holdout criterion in 1/3 trials, while memory-off and memory-on each passed 3/3. Both failing initials were corrected in one retry by either repair arm. No observed correctness or retry-count advantage from memory was established.

The studies plus their excluded smoke run used 11 actual Gemini calls, with $0.758626875 conservatively accounted at the declared rates. No budget-blocked arms or unknown-usage calls occurred. One visibly incorrect initial candidate passed the entire holdout suite, exposing a semantic coverage limitation despite complete method exercise. See [CLI_V3_LIVE_OBSERVATIONS.md](CLI_V3_LIVE_OBSERVATIONS.md) for the predeclared protocol, per-trial results, failure mechanisms, costs, and caveats. Structured report: `evidence/20261118-cli-v3-live-report/summary.json`.


## CLI v3 engineering validation (no new live inference)

The [retry-memory checkpoint](RETRY_MEMORY_OBSERVATIONS.md) expands the contract to 32 methods across five classes, with 44 visible and 28 holdout scenarios. All 32 methods have normal-return observations in both splits. Both runtimes detect all 16 injected visible-test defects.

A paired **synthetic replay** progressed from 82/88 to 86/88 to 88/88 visible observations in both repair arms; both selected candidates scored 56/56 holdout observations. One-shot scored 48/56 holdout. Repairs were predetermined: this validates orchestration, not a memory benefit or new Gemini translation accuracy. The prior live results below remain unchanged. Evidence: `evidence/20261117T231651Z-experiment-555a5519`; isolation audit: `evidence/20261117-retry-memory-v3-report`.


Latest: the stronger semantic suite and five-trial feedback comparison are complete.
See [semantic-v2 results](#november-17--stronger-semantic-suite-and-feedback-comparison),
including the budget-limited fifth comparison. The earlier pilot below is retained
as a separate study.

The live Commons CLI study now completed using Gemini 3.8 Flash and Docker:
three fresh initial translations, with the same initial candidate paired across
three arms. One-shot passed 2/3 trials; code repair and environment-plus-code
repair each passed 3/3. One natural missing-option recursion bug was fixed by
one Gemini repair call in each repair arm. No environment remediation was needed.
See [the live Commons CLI results below](#november-17-2026--live-commons-cli-results)
for evidence, denominators, and limitations. Earlier failed API attempts remain
recorded separately and are not silently replaced by this successful batch.

# Experiment checkpoint — October 19, 2026

Execution isolation, accuracy aggregation, and a bounded environment-remediation
policy are implemented and tested. **Live translation accuracy is now measured
for Levenshtein with Gemini 3.8 Flash:** all three independent one-shot
translations passed every visible and withheld case in both runtimes. The
earlier GPT-5.6 Sol attempt remains unvalidated because every request returned
HTTP 429; do not describe it as 0% model semantic accuracy.

## Reproduced baseline

[Baseline archive](evidence/20261019T221737Z-verification-160c3cc0/summary.json):
33 Python tests, five upstream Java test methods, and 276 successful final runtime
checks. This is the original synthetic replay on the public demo split.
A [final regression archive](evidence/20261019T223659Z-verification-5f569d8d/summary.json)
also passes all 50 current Python tests, the five Java tests, and the same 276 checks.

## Isolated expanded evaluation

[Isolation and fixture archive](evidence/20261019T223701Z-isolation-verification-a4a70745/summary.json):
50 Python unit/component tests and 11 real Docker integration tests passed.
The known-good fixtures passed all **946 runtime checks**:

| Task | Visible inputs | Withheld inputs | Passing checks across two runtimes |
| --- | ---: | ---: | ---: |
| Levenshtein | 26 | 140 | 332 / 332 |
| NormalizedLevenshtein | 26 | 124 | 300 / 300 |
| JaroWinkler | 26 | 131 | 314 / 314 |

These are 473 task/input combinations evaluated under CPython and GraalPy, not
946 independent samples or translated methods. The archive contains fixture
outputs, never live-model successes. Frozen suite SHA-256:
`1b67bef9154f6855a64697b81a929780d22dc65dfd0f7c87b85fa3b624877b47`.

The isolation tests exercise host-secret and repository exclusion, immutable
runner/candidate files, network denial, actual cgroup CPU/memory/PID limits,
process-count exhaustion, memory exhaustion, scratch exhaustion, timeouts,
output floods, missing-image rejection, GraalPy guest restrictions, and cache
remediation. They are explicit integration tests, not skipped Docker mocks.

## Earlier GPT-5.6 Sol attempt (unvalidated)

[Live trial archive](evidence/20261019T223008Z-experiment-7991f91c/summary.json):
three independent Levenshtein trial requests, `gpt-5.6-sol`, medium reasoning,
8192 requested output tokens per call, at most five shared repair rounds, dual
container runtimes, and a $1 conservative reservation budget. Source-derived
payload transfer was explicitly authorized. The exact prompts and sanitized
HTTP errors/request IDs are retained. No key was written into the repository,
containers, prompts, or artifacts.

All three initial requests returned HTTP 429. No initial translations or repairs
were produced; all nine planned arm/task/trial outcomes remain recorded as
unvalidated. The zero operational pass count reflects inability to evaluate, not
observed incorrect generated programs. There are no returned usage counts.
The $0.771975 in `spend.json` is retained conservative reservation for requests
with unknown usage, **not measured cost or a claim of charges**.

A [separate adapter diagnosis](evidence/20261019T223230Z-adapter-diagnosis-b9f2782a/result.json)
sent a tiny repository-free request and also received HTTP 429. The initial sanitized parser retained no more specific quota/rate-limit code.
The updated adapter now recognizes the current documented credit, organization,
and project limit codes for future diagnostics. The live study was then run
on Gemini instead; see the Live Gemini result below.
The diagnostic has its own small reservation within the original $1 allowance.
No provider key or arbitrary server body is logged.

## Controlled environment-repair evidence

[Synthetic stress archive](evidence/20261019T223104Z-experiment-80feac8d/summary.json):
one paired replay trial with an intentionally unwritable GraalPy cache in both
repair arms. The one-shot anchor uses the healthy environment.

| Arm | Outcome |
| --- | --- |
| Healthy one-shot, deliberately broken fixture | 4/26 visible and 18/140 withheld cases per runtime |
| Fixed-environment code repair | Trusted preflight fails; all planned cases remain unvalidated |
| Environment repair plus code repair | One cache remediation and one synthetic code repair; 26/26 visible and 140/140 withheld per runtime |

The E-Agent independently selected its allowlisted cache-path correction from
the trusted permission failure and repeated the probe. Its action consumed a
shared repair round. This demonstrates operational recovery under a controlled
fault. It is not evidence of live-model repair accuracy or broad autonomous
configuration repair.

## Live Gemini result

[Live Gemini archive](evidence/20261019T225222Z-experiment-b8857705/summary.json):
three independent Levenshtein trials, `gemini-3.8-flash` (resolved identity
unchanged across calls), medium thinking level, Gemini API free tier, at most
five shared repair rounds, 16384 output tokens per call including thinking, both
container runtimes, the same frozen suite (SHA-256 `1b67bef9…7b47`).

| Arm | Task/trials passing | Visible cases per runtime | Withheld cases per runtime |
| --- | ---: | ---: | ---: |
| One-shot | 3 / 3 | 78 / 78 | 420 / 420 |
| Code repair | 3 / 3 | 78 / 78 | 420 / 420 |
| Environment repair | 3 / 3 | 78 / 78 | 420 / 420 |

Every initial candidate passed all visible cases, so no repair was triggered and
the paired change is zero. The repair arms therefore measure nothing beyond the
shared one-shot result here. The descriptive Wilson 95% interval for a 3/3 task
pass rate is 43.8%–100%; three trials of one algorithm do not establish
generalization. Usage: 3 model calls, 10,320 input and 13,788 output tokens
(output includes thinking), no unknown-usage calls. The free tier is not
billed; `spend.json` shows $0.061 at paid list rates ($0.75/$3.75 per million),
recorded as a safety cap in case billing applied. Free-tier prompts may be used
by Google to improve its products; the prompts contain only the open-source
library under translation.

An [earlier attempt of this run](evidence/20261019T224716Z-experiment-5942d812/summary.json)
is preserved but excluded: in trial 1 a test file was added under `tests/`
while the run was in progress, and the integrity guard correctly invalidated it
after the candidate had passed 26/26 visible cases in both runtimes. Trials 2
and 3 of that attempt also passed every case. The clean rerun above changed no
protected file.

## Next empirical step

Run the same frozen protocol for NormalizedLevenshtein and JaroWinkler, and add
trials until some initial candidates fail, so the repair arms have something to
measure. Report the same model configuration and paired initial/final scores,
including genuine failed repairs and unchanged successes.

See [EXPERIMENTS.md](EXPERIMENTS.md) for commands, denominator definitions,
resource accounting, isolation details, and current limitations.

## Commons CLI stateful milestone — November 13, 2026 (local time)

Implemented a pinned Commons CLI 1.9.0 slice with four classes, 15 methods, and
three constructors. The host owns operation-sequence validation, Java oracle
execution, Python dispatch, exact trace comparison, bounded candidate selection,
and post-selection holdout scoring. The model supplies the candidate module only.
This is a scoped stateful adapter, not whole-repository translation.

Qualification evidence is archived in
[`evidence/20261114T025603Z-commons-cli-qualification-29b69468/summary.json`](evidence/20261114T025603Z-commons-cli-qualification-29b69468/summary.json).
Full inputs, repeated oracle traces, candidate sources, visible feedback, selection,
and holdout observations accompany it, with checksums.

- All **73 Python unit tests** passed, including 19 new contract/trace tests.
- The Java Maven test run passed; its upstream JUnit coverage remains the original
  string library, not Commons CLI upstream tests.
- The deliberately broken fixture passed **38/40 visible runtime checks** and
  **114/120 holdout runtime checks**. Its parser-reuse alias error was detected.
- After one synthetic replay repair, the selected fixture passed **40/40 visible**
  and **120/120 holdout** checks across CPython and GraalPy.
- All three original string-task acceptance runs still passed, totaling **276
  selected runtime checks** on their public demo visible/holdout sets.
- The updated guest-only Java container entry point compiled successfully with
  Java 21 compatibility. Docker was unavailable, so updated container images and
  their runtime behavior have not been verified here.

These results establish adapter/controller qualification using hand-written
fixtures. They do **not** measure LLM translation accuracy or repair effectiveness.
The 60 holdout sequences vary names and values across the same 20 templates;
independent semantic test expansion remains necessary. The scope uses Commons CLI
1.9.0 and is not matched to AlphaTrans. No paid model calls were made for this
milestone. See [EXPERIMENTS.md](EXPERIMENTS.md#commons-cli-milestone-stateful-qualification)
for commands and remaining research work.

## November 15, 2026 — Docker setup and Gemini diagnosis

Docker Desktop 29.9.3 is installed and running. Both current candidate images
built successfully; all 11 Docker integration tests passed. The Commons CLI
hand-authored fixture passed all 160 visible/holdout runtime checks in these
containers. These are infrastructure qualification results.

Live Commons CLI attempts did not yield a complete candidate:

- `20261115T215510Z-experiment-9d8225e6`: three initial Gemini 3.8 Flash requests
  with medium thinking and 16,384 output tokens. Two timed out at approximately
  120 seconds. One returned MAX_TOKENS: 40,186 input tokens, 15,729 thinking
  tokens, and 641 candidate tokens. All paired arms remain unvalidated.
- `20261115T220147Z-gemini-cli-extended-44d178cd`: a separate 300-second request
  configuration with 32,768 output tokens also returned MAX_TOKENS, with 31,326
  thinking tokens and 1,428 candidate tokens. This changed configuration is not
  pooled with the initial trials.
- `20261115T220605Z-gemini-cli-low-thinking-0f741955`: interrupted locally at the
  user's request to diagnose implementation before further experiments. Provider
  usage is unknown and its reservation is retained.
- A repository-free adapter probe (`runs/20261115T220728Z-gemini-adapter-diagnosis-8fe3ab44`)
  with low thinking and 1,024 output tokens timed out at 60 seconds. Model metadata
  lookup with the same key returned HTTP 200 and advertised generateContent.

Implementation findings: the controller hard-codes `min(120, remaining)` for model
requests; CLI `--timeout` configures execution processes, not model requests.
The transport uses non-streaming `generateContent`, so it provides no incremental
progress. The broad source bundle produces a 40,186-token prompt. Thinking shares
its output allowance with generated code and exhausted both tested allowances.
Incomplete responses are correctly rejected and not executed.

The tiny probe timing out means source-bundle size is not a sufficient explanation
for the timeouts. The precise cause of generation latency remains unresolved;
there is no evidence that Docker caused these API-stage failures. Next work is
transport/latency diagnosis and explicit request-timeout configuration, followed
by staged small-input generation checks before resuming translation experiments.
No Commons CLI live translation accuracy or repair improvement is established.
The combined conservative reservations/accounted amounts, including interrupted
and diagnostic calls, remain below $1; these are not measured provider charges.

### Previous-workload compatibility check and transport findings

One Levenshtein trial was rerun with `gemini-3.8-flash`, medium thinking, 16,384
output tokens, and a 120-second model timeout. The prompt matched the earlier
successful archive byte-for-byte. Every archived case input and reference was
retained; only the suite comparator fingerprint was explicitly rebound to the
current evaluator. This is a compatibility check, not an exact historical runtime
replication or a three-trial rerun.

The request timed out at 120.07 seconds while awaiting HTTP response headers.
No generated candidate reached Docker. See
`evidence/20261115T221252Z-experiment-1e2fba53` for the archived failed run.

A separate tiny curl generation probe returned HTTP **503**, with DNS at 0.037 s,
TCP connection at 0.094 s, TLS completed at 0.121 s, and first response byte at
2.840 s. TLS certificate verification succeeded. No proxy was configured. Thus
at least this request encountered an upstream availability failure, and the
observed problems are not limited to Commons CLI prompt size or Python response
parsing. This does not prove that every earlier timeout had the same cause.
No successful small-generation check has yet established readiness to resume.

Implemented a separate model-timeout CLI option and response-phase diagnostics.
All **75 unit tests** pass. Added `scripts/diagnose_gemini.py` for bounded,
repository-free transport diagnosis. On this Mac, Python's default CA file is
missing; the Python requests explicitly used `/etc/ssl/cert.pem`. That configuration
issue is distinct from the timeouts and HTTP 503 observed with verified TLS.

### Tiny Java-file smoke test

A single five-line `TinyAdd.java` file (`return a + b`) was submitted through
`GeminiBackend` using `gemini-3.8-flash`, low thinking, 2,048 output tokens,
and a 60-second model timeout. The smoke-test script uses the existing Docker
executor and evaluator, with eight Java reference inputs covering ordinary
addition and signed 32-bit overflow. Java oracle execution and both container
preflight checks passed before the API call.

The request timed out at **60.064 seconds while awaiting HTTP response headers**.
No Python candidate was returned and no translation comparison could run.
This reproduces the timeout without a large source bundle; it does not isolate
provider availability from account-specific or network-path behavior.
Evidence: `evidence/20261115T222245Z-tiny-java-smoke-955398c5/summary.json`.
Reproduce with `python3 scripts/smoke_java_translation.py` from `midpoint/`, with
Docker on PATH and a valid Python CA configuration. It loads the Gemini key from
the environment or ignored `.env`, makes one request with a $0.05 reservation
limit, and archives evidence whether the API succeeds or fails. This is a smoke
test, not a new benchmark task or an accuracy result.

## November 17, 2026 — live Commons CLI results

[Complete experiment archive](evidence/20261117T204352Z-experiment-1f46722d/summary.json).
The updated key first completed the tiny Java smoke test: Gemini returned a
translation in 2.955 seconds, and all 16 Java/Python comparisons passed inside
CPython and GraalPy containers. [Smoke evidence](evidence/20261117T204310Z-tiny-java-smoke-0e48207a/summary.json).
This establishes current operation, not that the earlier key caused all failures.

Configuration: Gemini `gemini-3.8-flash`, low thinking, 32,768 output tokens per
call, 300-second model request timeout, 90-second execution timeout, up to five
repair rounds, and a $1 conservative reservation cap for this batch. The frozen
Commons CLI suite SHA-256 was `ecd2f310dd9f38a7b098662dcc01f6010e885455203b20debf632bf9b558e352`.
Each trial used 20 visible and 60 holdout sequences. All candidate execution ran
inside the pinned Docker images; source, evaluator and tests were unchanged
during the study. Every selection was frozen before holdout scoring.

- **One-shot:** 2/3 fully passing trials; 108/120 visible runtime checks and
  324/360 holdout runtime checks across both runtimes (90% of checks).
- **Code repair:** 3/3 fully passing trials; 120/120 visible and 360/360 holdout
  runtime checks. Trials 1 and 2 needed no repair; trial 3 needed one live repair.
- **Environment plus code repair:** 3/3 fully passing trials; 120/120 visible
  and 360/360 holdout checks. Trial 3 independently needed one live code repair;
  no environment repair occurred in any trial.

Trial 3 initially passed 14/20 visible and 42/60 holdout sequences per runtime.
Its `getOptionValue` implementation resolved an absent option to `None`, then
recursively called itself with `None` rather than returning the default value.
This caused `RecursionError` in six visible scenarios. The trusted evaluator
reported the first differing operation; Gemini added a missing-value guard.
The repaired candidate preserved every previously passing visible case and
passed 20/20 visible plus 60/60 holdout sequences in each runtime. Only visible
feedback influenced repair; no manual edits were made to generated candidates.

There were **5 actual Gemini calls**: 3 initial translations and 2 independent
repairs. The nine arm/trial outcomes are not nine independent initial generations.
Usage was 239,550 input and 36,841 output tokens (including thinking), with no
unknown-usage calls. Conservative accounting was **$0.362732**, below the $1 cap;
this is not a provider invoice. All returned resolved model identities were
`gemini-3.8-flash`. Requests took approximately 42–53 seconds. The CLI returned
exit code 1 because the one-shot baseline failed one trial; the batch itself
completed and all outcomes were evaluated, with no unvalidated cases.

This is evidence of one natural live-model repair success on the scoped
four-class Commons CLI API. It does not establish a statistically reliable
advantage, whole-repository correctness, or additional benefit from environment
repair. Holdout inputs vary names and values across the same 20 scenario
templates; they do not establish independent semantic generalization. The
November 15 medium-thinking failed attempts used different configurations and
are not pooled with this low-thinking batch.

Next empirical priority: freeze a broader suite with independently designed
semantic scenarios (including partial-name ambiguity, option replacement and
more complex state reuse), qualify its oracle and adapters, then run fresh
paired trials. Do not reuse the current holdout as repair feedback or present
these three trials as evidence for repository-scale translation.

## November 17 — stronger semantic suite and feedback comparison

The `commons-cli-semantic-v2` profile has **36 visible and 20 holdout scenarios**.
Sixteen new visible cases cover partial-name ambiguity, exact matches, quoting,
option replacement, required-option changes, and parser reuse. Holdout sequences
are separately authored compositions, not randomized renamings of visible cases.
They still share API concepts and represent one small library slice. The seed is
recorded for provenance but these fixed scenario definitions do not use it.

Qualification used the Java oracle, repeated for stability, and an archived
Gemini baseline inside Docker. The baseline passed all **72 visible runtime
checks**. All **8 injected faults** were detected in both runtimes: alias loss,
parser-state leakage, missing-value corruption, wrong exception type, reversed
value order, disabled partial matching, ignored required flags, and ignored option
replacement. Only newly failing baseline-passing visible cases count as detections;
holdout was excluded from mutation qualification. These eight selected mutants
are an evaluator check, not a comprehensive mutation score or live-model result.
[Qualification evidence](evidence/20261117T222009Z-cli-semantic-qualification-3fda6c6b/summary.json).
A separate synthetic replay verified pairing and post-selection scoring before
live calls: [replay evidence](evidence/20261117T222142Z-semantic-ablation-replay-bd0f3849/experiment/summary.json).

The live study used **five fresh Gemini 3.8 Flash trials**, low thinking, 32,768
output tokens, a 300-second model timeout, a 90-second execution timeout, at most
three repairs, and a shared $1 reservation limit. Each trial paired the same initial
candidate with two feedback treatments. Basic feedback provides per-runtime pass
counts and execution status only. Operation feedback adds the first differing
operation, its expected/actual observation, and the preceding operation inputs.
Repair-arm execution order alternates across trials. All selections freeze before
holdout scoring; no trial receives a previous trial's fixes or feedback.

[Original run archive](evidence/20261117T222306Z-experiment-f3578eff/summary.json).
[Corrected reporting summary](evidence/20261117-semantic-v2-report/summary.json)
excludes blocked requests from evaluated repair counts and flags budget limits.
The original run archive is preserved unchanged; the report records its provenance.

Across CPython and GraalPy:

- **One-shot:** 3/5 fully passing trials; 310/360 visible and 184/200 holdout checks.
- **Basic feedback:** 4/5 fully passing trials; 338/360 visible and 192/200 holdout.
- **Operation feedback:** 4/5 fully passing trials; 332/360 visible and 192/200 holdout.

The aggregate equality of repair arms conceals a budget-limited comparison:

- Trial 4: the initial candidate passed 50/72 visible and 32/40 holdout checks.
  Basic feedback made two evaluated repairs without improvement and stopped under
  the no-progress rule. Operation feedback made one repair and reached 72/72
  visible and 40/40 holdout checks. It corrected recursive absent-option lookup.
- Trial 5: the initial candidate passed 44/72 visible and 32/40 holdout checks.
  Basic feedback reached 72/72 and 40/40 after two evaluated repairs. The operation
  feedback request was **blocked before a model call by the reservation cap**;
  the unchanged initial candidate was scored. This is not a failed Gemini repair
  and must not be used to infer that operation feedback is less effective.

There were **10 actual Gemini calls**: 5 initial translations, 4 basic-feedback
repairs, and 1 operation-feedback repair. Usage was 439,522 input and 71,466 output
tokens, including thinking, with no unknown-usage calls. Conservative accounting
was **$0.680049**. The final request's worst-case reservation exceeded the remaining
allowance even though recorded accounting was below $1. These amounts are not a
provider invoice. A reporting fix now distinguishes attempted, evaluated, and
budget-blocked repairs; all **81 unit tests** pass.

This provides one fully observed paired example where operation feedback helped
and basic feedback did not. Five trials on one slice, with one budget-confounded
comparison, do not establish a statistically reliable ranking. Do not pool this
suite with the earlier pilot or claim nine/15 independent initial generations.

Next work: reserve equal repair capacity for each paired arm before another
feedback study, expand subjects, and then add dependency-ordered multi-module
translation. Whole-repository translation and cross-trial lesson reuse remain
unimplemented. A future lesson-reuse study must be separately labelled and keep
evaluation holdout behavior out of the learned context.
