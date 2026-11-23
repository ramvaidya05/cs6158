# Project summary

Last updated: **November 23, 2026**. Latest live study: November 22 local time, paired Validator runtime diagnosis.

## Goal and implementation

Translate selected Java library behavior into Python using an LLM, then verify and repair it against the original Java implementation. The LLM proposes code; the harness controls acceptance.

- Live Gemini API integration and Docker execution are working. Generated Python is checked in **CPython and Java-embedded GraalPy** against a pinned Java reference.
- Frozen visible tests guide repairs; separate holdout tests evaluate final selected candidates. Paired experiment arms share the same initial translation.
- Guardrails include dependency checks, bounded environment actions, independent spending budgets, time/token limits, and best-checkpoint retention. Recent studies allow up to **three repairs**, stopping earlier on success, repeated code, or lack of progress.
- Pruned error feedback, per-attempt `requirements.txt`, and optional `TRANSLATION_FAILURES.md` retry history are implemented. History stays within its own trial/arm; it is **not model training or cross-trial learning**. Only standard-library dependencies are currently approved.
- Evidence includes prompts, responses, candidates, execution results, usage, and checksums. Live experiments and synthetic harness tests are reported separately.

## Important experiment results

- **Early pilot:** live Levenshtein translations passed all checks in 3/3 one-shot trials. Earlier API failures/timeouts remain documented as unsuccessful runs.
- **Commons CLI v3:** 32 methods across five classes; 44 visible and 28 holdout scenarios. Main study: all three initial translations passed, so repair offered no measurable improvement. Separate memory study: full-task success improved from **1/3 one-shot to 3/3 with either repair arm**. Both failures needed one retry. **Memory added no measured benefit.** The scoped CLI study is complete; the full library is not translated.
- **CLI v4:** the new holdout detected the archived nullable lookup defect. Full-suite passes were 1/3 with full context and 2/3 with compact guided context. The compact arm used 60.6% fewer input tokens. [Study details](midpoint/CLI_V4_CONTEXT_OBSERVATIONS.md).
- **Commons CSV parser/printer milestone complete:** v2 uses a 65% smaller source prompt with Java semantic guidance and a fresh suite of 101 development and 59 holdout cases. Full-suite passes improved from **0/3 one-shot to 3/3 in each repair arm**, after one retry each. v1 memory added no measured accuracy benefit. Headers and broader APIs remain outside this scope.
- **Commons Codec Hex:** the live v2 continuation reached 110/110 CPython and 108/110 GraalPy holdout cases. An assisted Unicode fix passed 131/131 API cases and all 65,536 Java character digit checks per runtime. [Evidence](midpoint/CODEC_V2_OBSERVATIONS.md).

- **Commons Validator Luhn:** the pilot selected 126/130 holdout cases per runtime. An assisted fix later passed 160/160 regression cases per runtime. [Evidence](midpoint/VALIDATOR_OBSERVATIONS.md).

- **Fresh paired Validator study:** diagnosis and semantic guidance achieved **2/3** full passes versus **0/3** with ordinary repair. The remaining failure involved isolated surrogate inputs in GraalPy. A subsequent factorial study stopped on truncated output before completing any paired comparison. [Paired study](midpoint/PAIRED_DIAGNOSIS_OBSERVATIONS.md) · [Factorial attempt](midpoint/FACTORIAL_DIAGNOSIS_PROTOCOL.md).

CLI v3 used 11 live calls (~**$0.76**), CSV v1 used 32 (~**$2.59**), and CSV v2 used nine (~**$0.43**). Costs use declared accounting rates. After integrating CSV, Codec and Validator, **145 Python tests passed**. The existing CSV Java qualification passed **10 tests**.

## What the evidence supports—and what remains

Execution-guided repair helped failing translations in these small studies. Retry memory has **not shown an accuracy advantage**. Healthy CLI/CSV studies required no environment actions; separate controlled fault tests demonstrate only the implemented recovery path. Three trials and correlated checks in two runtimes do not establish broad statistical superiority. Passing these suites does not prove full semantic equivalence.

**Next:** replicate the CLI context comparison across more trials and subjects, and revise the Validator factorial output budget before rerunning. Broader dependency handling, repository translation and a matched AlphaTrans comparison remain open.

## Details only when needed

- [Complete experiment history](midpoint/EXPERIMENT_RESULTS.md)
- [CLI results](midpoint/CLI_V3_LIVE_OBSERVATIONS.md) · [CSV v2 results and verified translation](midpoint/CSV_V2_OBSERVATIONS.md)
- [Codec completion and provenance](midpoint/CODEC_V2_OBSERVATIONS.md)
- [Retry memory and dependency changes](midpoint/RETRY_MEMORY_OBSERVATIONS.md)
- [Architecture and roadmap](IMPLEMENTATION_PLAN.md) · [Professor feedback response](midpoint/REVIEWER_RESPONSE.md)

**Maintenance:** update this file after meaningful implementation, experiment, or plan changes. Replace outdated status instead of appending a diary; keep it short and link detailed evidence. Updating the summary date does not imply new experiments ran.

[Failure taxonomy and evidence](midpoint/FAILURE_TAXONOMY.md).
