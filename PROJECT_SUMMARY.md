# Project summary

Last updated: **November 21, 2026**. Latest recorded Codec experiments and qualification: November 21 local time.

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
- **Commons CSV v1:** parser/printer interfaces; 37 visible and 28 holdout scenarios. Across three main trials, average holdout accuracy increased from **73.81% to 92.86%** with repair. Code repair passed all visible cases, but **0/3 candidates passed the entire suite**. Remaining errors include escaping and Java UTF-16 delimiter semantics. Separate memory study: identical final accuracy with/without history; history saved one retry in one pair.
- **Commons Codec Hex:** separately recorded three-trial study reached **96.8% CPython / 90.9% GraalPy holdout accuracy**, but **0/3 full-task passes**. A November 21 v2 live trial plus continuation reached 110/110 CPython and 108/110 GraalPy holdout cases (12,119 tokens). A subsequent developer-assisted Unicode fix completed the supported Hex slice: 21/21 visible and 110/110 previously withheld cases in each runtime, plus all 65,536 Java char digit mappings in each. This qualification used no API tokens; it is regression evidence, not autonomous repair success or full-library completion. Different model/settings mean this is not a matched comparison with CLI/CSV.

CLI v3 used 11 live calls (about **$0.76**); CSV used 32 (about **$2.59**), including their smoke runs. These are declared-rate accounting estimates, not provider invoices or total historical project spend. Latest validation checkpoint: **127 Python tests passed**; CSV Java qualification passed **10 tests**.

## What the evidence supports—and what remains

Execution-guided repair helped failing translations in these small studies. Retry memory has **not shown an accuracy advantage**. Healthy CLI/CSV studies required no environment actions; separate controlled fault tests demonstrate only the implemented recovery path. Three trials and correlated checks in two runtimes do not establish broad statistical superiority. Passing these suites does not prove full semantic equivalence.

**Next:** turn observed CSV failures and CLI absent-option coverage gaps into development regressions; create versioned suites with fresh independent holdout cases before another scored study. Preserve old scores and archives. Broader CSV APIs, multi-module/repository translation, cross-trial learning, arbitrary package installation, and a matched AlphaTrans comparison remain outstanding.

## Details only when needed

- [Complete experiment history](midpoint/EXPERIMENT_RESULTS.md)
- [Codec completion and provenance](midpoint/CODEC_V2_OBSERVATIONS.md)
- [CLI results](midpoint/CLI_V3_LIVE_OBSERVATIONS.md) · [CSV results](midpoint/CSV_LIVE_OBSERVATIONS.md)
- [Retry memory and dependency changes](midpoint/RETRY_MEMORY_OBSERVATIONS.md)
- [Architecture and roadmap](IMPLEMENTATION_PLAN.md) · [Professor feedback response](midpoint/REVIEWER_RESPONSE.md)

**Maintenance:** update this file after meaningful implementation, experiment, or plan changes. Replace outdated status instead of appending a diary; keep it short and link detailed evidence. Updating the summary date does not imply new experiments ran.
