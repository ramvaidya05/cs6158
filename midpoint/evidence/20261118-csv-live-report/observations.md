# CSV v1 live-study observations

Date: November 17, 2026 (America/New_York).

## Predeclared protocol

Use the already frozen `commons-csv-v1` suite, SHA-256 `1dd4307ef5aa8683508991d07078cd81d29878d723b78ec45051de9a28a2ea3f`: Commons CSV 1.10.0, two scoped entrypoints, 37 visible and 28 separately authored holdout scenarios. No changes to cases, expected observations, candidate code, or evaluator behavior during the study.

First run one live smoke translation, excluded from cohort statistics. If API generation and isolated evaluation work, run three fresh paired trials: one-shot, code repair, environment-aware repair. All three arms reuse their trial's initial response verbatim. Main-study repair feedback retains the existing full visible-feedback mode; memory is disabled. Healthy containers are used, so environment repair may have no opportunity to act.

Run a separate three-trial memory-on/off cohort only if the main cohort has at least one visible initial failure and no operational blocker. Its arms use identical pruned current feedback, differing only in local accumulated history; arm order alternates. Never transfer lessons across trials or reuse main-study candidates as fresh memory-cohort initials. If all main initial candidates pass, skip this optional cohort and record the lack of repair opportunities.

Settings: Gemini `gemini-3.8-flash`, low thinking, 32,768 output tokens per call, 131,072 per-arm output-token allowance, up to three repairs, 300-second model timeout, 90-second execution timeout, and 1,200-second loop deadline. Existing early stopping and non-regressing checkpoint selection apply. All cohort selections freeze before any holdout scoring.

Use the same supplied accounting rates as the completed CLI study: $0.75/M input with the existing 1.25 premium, and $3.75/M output. These are experiment accounting assumptions, not verified current provider prices or invoice amounts. Independent caps: $0.40 smoke; $8 main cohort; $8 optional memory cohort. Each three-trial study requires $7.93548 conservative reservation capacity before API calls. Maximum combined cap is $16.40 if all phases run. The 272,000 input-allowance guard stays enabled; no automatic cap increase or context truncation is allowed.

The source prompt is large. Measure the smoke request's reserved input allowance and inspect space for the generated candidate plus feedback before starting repairs. If the request-size guard blocks a phase, retain its evidence and revise context only under a separately recorded protocol, not midway through scored trials.

Runner: `scripts/run_csv_v1_study.py --phase smoke|main|memory --suite evidence/20261118-csv-adapter-report/suite.json`. Raw evidence is archived even for failures. Synthetic CSV probe/replay results remain separate from live model results.

## Results

Smoke completed on both runtimes: 35/37 visible and 25/28 holdout scenarios per runtime (70/74 and 50/56 combined). The candidate failed escape handling and invalid configuration checks. This is a translation failure, not an API/container failure. No smoke result is included in cohort statistics, and no prompt or suite changes were made in response.

The actual first-call reserved input allowance was 221,436. The candidate was 22,688 UTF-8 bytes. The full visible-feedback repair prompt's JSON-wrapped allowance lower bound was 246,155, leaving headroom under 272,000 for provider fields. Smoke cost was $0.07467375 at the declared accounting rates. Archive: `evidence/20261118T023453Z-csv-v1-smoke-eaa5fa4d`.

An initial local preflight attempt stopped before any API call because the merged credential loader expected `.env.gemini`. The staged runner was adapted to also read the user's existing `.env` Gemini entry without shell evaluation or credential logging. No key file was changed.

### Main cohort: completed

Archive: `evidence/20261118T023644Z-csv-v1-main-19f9796b`. Three paired trials, 17 live model calls, $1.373619375 accounted cost. No unknown-usage calls.

Scores below are per runtime; CPython and GraalPy agreed. They are repeated observations of the same candidate, not six independent trials.

- One-shot visible: 35/37, 34/37, 20/37; holdout: 25/28, 25/28, 12/28.
- Code repair visible: 37/37 in all three trials after two repairs each; holdout: 26/28 in all three.
- Environment-aware repair visible: 37/37, 36/37, 36/37; holdout: 26/28 in all three. Repair counts: two, three, three. Trial 2 stopped for no progress; trial 3 exhausted the repair limit. Best-checkpoint selection preserved earlier improvements.
- Complete visible-plus-holdout success: 0/3 for every arm. Mean holdout case accuracy increased from 73.81% one-shot to 92.86% in both repair arms; this descriptive average is based on only three trials and a fixed small suite.

The two recurring held-out failures concern escaped delimiters/newlines and supplementary-character delimiters (Java UTF-16 character validation). Passing all visible tests did not establish general equivalence. These observations were not supplied to repair calls or used to change the frozen cohort.

No environment actions were applied. Healthy containers offered no environment-repair opportunity; differences between repair arms cannot establish an environment-treatment benefit. This cohort supports bounded code-repair improvement on the scoped interface, not full-library translation or statistical superiority.

The paired initial hashes, final selection hashes, absence of holdout case IDs in prompts/history, and absence of configured credentials in archived files passed the automated audit. The case-ID check is a limited leakage check, alongside the controller's separate visible/holdout paths; it is not a proof that every possible semantic overlap is absent.

### Memory cohort

Archive: `evidence/20261118T025213Z-csv-v1-memory-31a71c69`. Three fresh paired trials used identical pruned current feedback and local history enabled only in `memory_on`. The main cohort had visible initial failures, satisfying the predeclared gate. No main-cohort candidate or failure lesson was reused.

- One-shot visible: 35/37 in all three trials; holdout: 26/28, 24/28, 24/28 per runtime.
- Both memory-off and memory-on selected visible scores: 37/37, 36/37, 37/37; holdout: 27/28, 25/28, 25/28. Both runtimes agreed.
- Repair calls: memory-off 1, 3, 2; memory-on 1, 3, 1. In trial 2, memory-off stopped for no progress and memory-on stopped after emitting a byte-identical repeated candidate. Both retained their first improved checkpoint.
- Complete visible-plus-holdout success: 0/3 in every arm. Mean holdout case accuracy: 88.10% one-shot, 91.67% in both repair arms.
- Fourteen live calls, $1.1406346875 accounted, no unknown-usage calls. Initial generation cost $0.22623; six memory-off repair calls cost $0.4962684375; five memory-on repair calls cost $0.41813625.

There is no measured final-accuracy benefit from history in this cohort. One paired trial required one fewer repair with history, but three trials are insufficient to establish a reliable efficiency benefit. A history document did not prevent repeated mistakes in trial 2. The cohorts have different fresh initial candidates and feedback modes; their aggregate differences do not isolate pruning or memory as a cause.

## Integrity, scope, and next work

All three phases resolved to `gemini-3.8-flash`. Total: 32 real API calls, $2.5889278125 accounted, zero unknown-usage calls. These are accounting estimates, not invoice charges. Largest reserved input allowances were 221,436 smoke, 248,570 main, and 254,779 memory, all below 272,000. No context guard was bypassed, no operational failure was observed, and no environment actions were applied.

The reproducible audit in `evidence/20261118-csv-live-report/audit.py` checks paired initial hashes, selected-file hashes, absence of holdout IDs in prompts/history, history enabled only in its designated arm, and absence of locally configured credential values. The final Python regression run passed all 125 tests. Prior clean Java qualification passed all 10 tests; no Java changes followed it. Raw evidence remains unchanged and separately checksummed.

This completes the first live CSV parser/printer slice, not all Commons CSV APIs or repository migration. Next, classify the unresolved behaviors from archived evidence, add them as explicit development regressions in a versioned follow-up, and independently author a new holdout before any new scored run. The now-inspected v1 holdout cannot remain a fresh confirmation set after tuning. Broader headers/record APIs and dependency-aware decomposition need separate scope and feasibility gates. Retain memory as an optional feature; do not claim an accuracy advantage from these results.
