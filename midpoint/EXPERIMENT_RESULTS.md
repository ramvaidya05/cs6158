# Experiment checkpoint — November 13, 2026

## November 13: continued trials and evaluator sensitivity

Two new fixed batches each admitted three NormalizedLevenshtein and three
JaroWinkler task/trials with unchanged Gemini 3.8 Flash settings and the original
frozen suite. The [remaining-allowance batch](evidence/20261113T225208Z-experiment-f7ea06a7/summary.json)
made two requests that timed out and then stopped at its $0.20 reservation cap.
After the user approved an additional $1, the [newly funded batch](evidence/20261113T235626Z-experiment-78be7f18/summary.json)
made three requests that timed out, triggering the three-failure availability
guard. In each batch, seven arm records ended in error and eleven remained
explicitly unrun. No candidates were produced, so neither batch supplies a new
semantic accuracy estimate. Retained conservative reservations are $0.161652
and $0.243631 respectively; actual usage/charges are unknown.

The [verified experiment history](reports/20261113-experiment-history.md)
now covers all eight translation experiment archives, including failed and
integrity-invalidated runs. Its [JSON report](reports/20261113-experiment-history.json)
contains per-task details and accounting. Report inspection no longer overwrites
archived summaries; checksum verification rejects modified, missing, extra, or
escaping files, and duplicate archives cannot be counted twice. All **66 Python
tests pass**, including the reporting integrity tests.

A separate [semantic sensitivity experiment](evidence/20261114T000258Z-semantic-sensitivity-27e8061d/summary.json)
froze seven deliberate fixture mutations before scoring them in both containers.
All three correct controls passed **946/946 runtime checks**. All **7/7 mutations
were detected in both runtimes**. Mismatch counts below are per runtime and were
identical in CPython and GraalPy:

| Synthetic fault | Visible mismatches | Withheld mismatches |
| --- | ---: | ---: |
| Levenshtein uses Unicode code points | 2 | 48 |
| Levenshtein ignores its limit | 4 | 31 |
| NormalizedLevenshtein uses code points | 2 | 92 |
| Normalization divides by the shorter length | 13 | 65 |
| JaroWinkler replaces binary32 arithmetic with binary64 | 8 | 103 |
| JaroWinkler caps its prefix at four | 1 | 47 |
| JaroWinkler uses fractional rather than integer transpositions | 0 | 30 |

The last mutation exposes an important feedback limitation: a candidate can pass
every visible case yet fail the withheld score. That failure must not feed back
into the same trial's repair prompts. The frozen suite and prompts were not
changed after observing these results. Any stronger visible-test protocol must
be a separately versioned future study. Mutation detection measures evaluator
sensitivity to these seven selected faults, not model translation accuracy,
general test completeness, or effectiveness of live code repair. No model calls
were made in this experiment.

## November 11 checkpoint

The reporting pipeline now separates algorithm results, operational pass rates,
completion rates, visible-failure repair opportunities, full recoveries, and
withheld-case regressions. The live runner accepts Gemini credentials through a
hidden, memory-only prompt; optional local credentials use a separate ignored
owner-only file. At this checkpoint, **61 Python tests and 11 actual Docker
isolation tests passed.**

The [expanded Gemini attempt](evidence/20261111T232307Z-experiment-6d8f99ec/summary.json)
admitted three trials each of Levenshtein, NormalizedLevenshtein, and JaroWinkler
before generation, with the existing model/configuration and frozen pilot suite.
No candidate was produced: four requests timed out at 120 seconds, two returned
HTTP 503 `UNAVAILABLE` with a high-demand explanation, two failed at transport,
and the ninth initial request was blocked by the $0.65 reservation cap. All nine
initial task/trials and their paired arms remain unvalidated. **No new semantic
accuracy estimate is available.** The $0.642397 retained reservation is unknown
usage accounting, not measured cost or a claim that charges occurred.

A non-generating model metadata request authenticated successfully. A separate
[tiny generation diagnosis](evidence/20261112T014417Z-gemini-diagnosis-ce6c3e0d/result.json)
also timed out after 20 seconds, retaining a $0.004933 reservation. Together these
support a generation-availability problem; the exact cause of each timeout is
unknown. No model switch or hidden retry was made.

This failure motivated an implemented, tested availability guard: three consecutive
transient provider failures stop new requests, while authentication/access/quota,
budget, and model-identity failures stop immediately. Future batches preserve
unrun admitted trials and save the stop evidence. This policy was added **after**
the archived failed batch; the historical records have not been changed.

The [recorded Gemini recovery study](evidence/20261112T014615Z-recorded-gemini-stress-f10fc0f9/summary.json)
then reused the unchanged Levenshtein candidate from trial 0 of the October live
archive, with original prompt/response copies and verified hashes. It made **zero
model calls**. The healthy one-shot arm passed all 26 visible and 140 withheld
inputs in each runtime. Under the same deliberately unwritable GraalPy cache,
the fixed-environment arm failed preflight; the environment agent independently
selected one allowlisted cache correction, repeated its probe, and passed all
332 runtime checks with the unchanged candidate. This establishes bounded
operational recovery on recorded model-generated code, not fresh translation
accuracy or code-repair improvement. The planned fresh-model, three-task fault
study remains deferred because generation was unavailable.

The results below remain the earlier October checkpoint and are retained for
comparison.

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

When generation is available, run a newly admitted fixed-size batch for
NormalizedLevenshtein and JaroWinkler with the same model/configuration. Keep the
failed batch in the cumulative operational record. Do not extend trials until a
desired repair opportunity or improvement appears. Report zero opportunities
when all initial candidates pass; use harder, independently frozen subjects to
study genuine code repair. The current expanded pilot suite is exposed, not a
fresh blind holdout.

See [EXPERIMENTS.md](EXPERIMENTS.md) for commands, denominator definitions,
resource accounting, isolation details, and current limitations.
