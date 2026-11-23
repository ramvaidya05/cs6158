# Paired runtime-diagnosis study

Protocol implemented November 22, 2026 (America/New_York).

## Question and treatment

Does adding trusted runtime capability diagnosis and a source-runtime decimal
contract improve repair over ordinary visible-test feedback for the scoped
Commons Validator Luhn translation? This evaluates portability guidance, not
cache repair, arbitrary dependency installation, or whole-library translation.

Three fresh Gemini 3.5 Flash initial translations are each shared by two arms:
ordinary code repair and diagnosis-guided code repair. Each arm has at most one
repair call, identical model/thinking/output settings, identical visible cases,
and the same per-case non-regression selection rule. Arm order alternates.
The diagnosis arm additionally receives CPython/GraalPy capability probes and
a Java-derived decimal-block contract. No deterministic candidate edits occur.
This combined treatment cannot isolate probe benefit from semantic-contract benefit.

30 visible cases reuse the development protocol. A new deterministic seed
2026112201 generates 136 withheld cases including decimal strings, Unicode digit
blocks, invalid inputs, UTF-16 surrogate inputs, and longer strings. Java oracle
results are repeated before inference. All selections freeze before any withheld
candidate evaluation. Previously inspected suites are not used for final scoring.

## Budget and endpoints

Maximum nine calls, 4,096 output tokens per call, three independent trial envelopes
of $0.50/3. Declared accounting rates: $1.50 input / $9.00 output per million,
with the harness's conservative input premium. Shared initial calls are charged
once. Unused envelopes do not transfer. A provider/budget failure stops the study
and remains archived; incomplete pairs cannot count as successful trials.

Primary endpoint: all visible and withheld cases pass in both runtimes.
Secondary endpoints: per-runtime case accuracy, accepted repairs, regressions,
model calls, input/output/thinking tokens, elapsed time, and accounted cost.
The two runtimes are correlated checks, not separate independent trials.
With three pairs, discordant outcomes are descriptive evidence, not a reliable
population-level superiority claim. Report wins/ties/losses, including failures.

## Remaining causal questions

A separate controlled infrastructure experiment must compare recovery with and
without allowlisted environment actions, under healthy and injected-fault
conditions. A cache-recovery test is evidence about that fault mechanism; it
cannot establish general translation accuracy gains. Further independent trials
and subjects are needed before broad claims about environment-aware agents.

## Observed results — November 22 local time

Archive: `evidence/20261123T015139Z-validator-paired-diagnosis-7c6aa7be`.
All 140 archived files verified against checksums. Nine requests completed with
known usage: **35,225 tokens**, **$0.182825625 accounted**, **188.307 seconds**
including preparation, diagnosis and evaluation. All **141 Python tests passed**.

| Trial | Ordinary repair CPython/GraalPy holdout | Diagnosis CPython/GraalPy holdout | Full-task winner |
|---|---|---|---|
| 0 | 113/136, 113/136 | 136/136, 136/136 | Diagnosis |
| 1 | 113/136, 113/136 | 136/136, 136/136 | Diagnosis |
| 2 | 135/136, 135/136 | 136/136, 133/136 | Neither |

Ordinary repair was rejected in all three pairs by the visible non-regression
gate, retaining initials at 28/30 visible cases per runtime. Diagnosis repair was
accepted in all three pairs, reaching 30/30 visible per runtime. Full-task success
was **0/3 ordinary versus 2/3 diagnosis**: two wins, one tie, zero losses on the
primary endpoint. The third diagnosis candidate regressed GraalPy holdout accuracy
from 135/136 to 133/136 despite improving visible cases. Its `isValid` behavior
on three isolated-surrogate strings raised an exception instead of returning false.
The evaluator retained these failures; no post-scoring correction was made.

Pooled case-trial accuracy per runtime: ordinary **361/408 (88.48%)** in each;
diagnosis **408/408 (100%) CPython**, **405/408 (99.26%) GraalPy**. Repeated cases
across candidates do not create 408 independent experimental units. All arms
used actual model output with no deterministic substitution or manual edits.

This provides small-sample evidence for the combined diagnosis-plus-contract
feedback intervention on Luhn portability. It does not establish broad agent
superiority or successful infrastructure remediation. Only two pairs are
non-ties on full-task success; more independent trials and subjects are needed.
Freeze a new suite before follow-up after inspecting these failures. A factorial
comparison separating capability diagnosis from semantic contract hints would
clarify which part of the treatment contributed to the observed improvement.
