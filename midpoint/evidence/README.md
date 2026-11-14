# Midpoint evidence

`20261019T214029Z-verification-1aee5b7b/` is the completed acceptance archive.
Its summary records three synthetic replay tasks, 138 task/case combinations,
276 passing final runtime checks, and five passing upstream JUnit test methods.
`unit-tests.json` records all 33 passing Python tests. Per-task directories hold
the prompts, candidates, reference outputs, execution logs, and comparisons.

These results validate the harness, not LLM translation performance. The initial
candidate was deliberately broken and the replacement fixtures were hand-authored.
The public withheld split was excluded from repair prompts but is not a private
research evaluation set.

`setup-failure-graal-cache/` preserves an earlier real infrastructure failure.
It is separate from the successful acceptance results and is not scored as a
translation failure.

Reproduce with `python3 scripts/bootstrap.py` followed by
`python3 scripts/verify.py --archive` from the project root. Each invocation makes
a new archive; retain prior evidence unchanged. Absolute paths in historical
logs describe the machine used for that run and are not portable configuration.

## Post-midpoint evidence

See [EXPERIMENT_RESULTS.md](../EXPERIMENT_RESULTS.md) for the reproduced baseline,
expanded container fixture validation, failed GPT-5.6 Sol requests, the live
Gemini 3.8 Flash Levenshtein study (`20261019T225222Z-experiment-b8857705`, 3/3
trials passing every case), an excluded integrity-invalidated attempt of that
study (`20261019T224716Z-experiment-5942d812`), and a separately labeled synthetic
environment-remediation experiment. Failed and invalidated runs are retained.

November 11 additions:

- `20261111T232307Z-experiment-6d8f99ec`: fixed three-task live Gemini batch;
  no generated candidates, provider timeouts/503/transport failures and a final
  budget stop. Every admitted task/trial remains in the report.
- `20261112T014417Z-gemini-diagnosis-ce6c3e0d`: tiny repository-free generation
  timeout, with a retained conservative spend reservation.
- `20261112T014615Z-recorded-gemini-stress-f10fc0f9`: unchanged archived Gemini
  candidate; healthy and autonomously repaired environments pass all cases;
  fixed environment fails the injected cache fault. Zero fresh model calls.

Directory timestamps are UTC; the latter two were November 11 in New York.

November 13 additions:

- `20261113T225208Z-experiment-f7ea06a7`: six admitted task/trials, two timeout
  calls, then a reservation-budget stop; no generated candidates.
- `20261113T235626Z-experiment-78be7f18`: six admitted task/trials, three timeout
  calls, then an automatic provider-availability stop; no generated candidates.
- `20261114T000258Z-semantic-sensitivity-27e8061d`: seven predeclared synthetic
  mutations detected in both runtimes and 946/946 correct-control checks passing.
  One mutation escaped visible tests but failed withheld scoring. No model calls.

The [experiment history](../reports/20261113-experiment-history.md) verifies and
compares all eight translation experiment archives without rewriting them.
Synthetic sensitivity evidence is separate from translation pass-rate reporting.
