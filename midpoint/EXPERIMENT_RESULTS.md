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
