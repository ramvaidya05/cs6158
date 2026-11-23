# Project summary

Last updated: **November 22, 2026**. Latest live study: November 22 local time, paired Validator runtime diagnosis.

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
- **Commons CSV parser/printer milestone complete:** v2 uses a 65% smaller source prompt with Java semantic guidance and a fresh suite of 101 development and 59 holdout cases. Full-suite passes improved from **0/3 one-shot to 3/3 in each repair arm**, after one retry each. v1 memory added no measured accuracy benefit. Headers and broader APIs remain outside this scope.
- **Commons Codec Hex:** separately recorded three-trial study reached **96.8% CPython / 90.9% GraalPy holdout accuracy**, but **0/3 full-task passes**. A November 21 v2 live trial plus continuation reached 110/110 CPython and 108/110 GraalPy holdout cases (12,119 tokens). A subsequent developer-assisted Unicode fix completed the supported Hex slice: 21/21 visible and 110/110 previously withheld cases in each runtime, plus all 65,536 Java char digit mappings in each. This qualification used no API tokens; it is regression evidence, not autonomous repair success or full-library completion. Different model/settings mean this is not a matched comparison with CLI/CSV.

- **Commons Validator Luhn pilot:** selected translation passed **126/130 holdout cases (96.92%)** per runtime; **0/1 full-task success**. The repair improved CPython visible cases but regressed GraalPy and was rejected. A runtime-guided continuation also failed. A deterministic assisted API substitution then passed **160/160 cases per runtime**. Total live usage: **13,055 tokens**, about **$0.074** accounted; assisted qualification used no API calls. This is scoped regression success, not autonomous model repair. [Protocol and evidence](midpoint/VALIDATOR_OBSERVATIONS.md).

- **Fresh paired Validator study:** ordinary repair **0/3** versus diagnosis-guided repair **2/3 full-task passes**, with shared initial candidates and a fresh 136-case holdout. No manual candidate edits. Third diagnosis candidate failed three GraalPy surrogate cases. Nine calls, **35,225 tokens**, **$0.183** accounted. This supports the combined runtime/semantic guidance treatment on one small task, not general superiority. [Evidence](midpoint/PAIRED_DIAGNOSIS_OBSERVATIONS.md).

CLI v3 used 11 live calls (~**$0.76**), CSV v1 used 32 (~**$2.59**), and CSV v2 used nine (~**$0.43**). Costs use declared accounting rates. After integrating CSV, Codec and Validator, **145 Python tests passed**. The existing CSV Java qualification passed **10 tests**.

## What the evidence supports—and what remains

Execution-guided repair helped failing translations in these small studies. Retry memory has **not shown an accuracy advantage**. Healthy CLI/CSV studies required no environment actions; separate controlled fault tests demonstrate only the implemented recovery path. Three trials and correlated checks in two runtimes do not establish broad statistical superiority. Passing these suites does not prove full semantic equivalence.

**Next:** resume the four-arm diagnosis/semantic-guidance question under a revised predeclared output policy. Its first attempt stopped on incomplete model output (three calls, $0.083; no complete comparisons). [Protocol and failed evidence](midpoint/FACTORIAL_DIAGNOSIS_PROTOCOL.md). Replicate on other subjects and evaluate controlled infrastructure recovery. Close CLI absent-option coverage gaps with fresh holdout cases. Multi-module translation, cross-trial learning, arbitrary package installation, and a matched AlphaTrans comparison remain outstanding.

## Details only when needed

- [Complete experiment history](midpoint/EXPERIMENT_RESULTS.md)
- [CLI results](midpoint/CLI_V3_LIVE_OBSERVATIONS.md) · [CSV v2 results and verified translation](midpoint/CSV_V2_OBSERVATIONS.md)
- [Codec completion and provenance](midpoint/CODEC_V2_OBSERVATIONS.md)
- [Retry memory and dependency changes](midpoint/RETRY_MEMORY_OBSERVATIONS.md)
- [Architecture and roadmap](IMPLEMENTATION_PLAN.md) · [Professor feedback response](midpoint/REVIEWER_RESPONSE.md)

**Maintenance:** update this file after meaningful implementation, experiment, or plan changes. Replace outdated status instead of appending a diary; keep it short and link detailed evidence. Updating the summary date does not imply new experiments ran.
