# CSV adapters and frozen evaluation

Date: November 17, 2026 (America/New_York).

## Implemented

`commons_csv` is now an executable task in the shared controller and experiment CLI. Its two candidate functions are `parse_csv(text, config)` and `print_csv(records, config)`. Both CPython and GraalPy use the same trusted adapter; the candidate receives copies of record/configuration data and must return typed nested string/null lists or a string. Model context contains the pinned Java sources and contract, not evaluation cases or expected observations.

CSV comparison is exact, independently of the numeric benchmarks: field/record order, null versus empty string, whitespace, Unicode, quoting, and printer line endings are preserved. Exceptions compare by declared category (`CSVParseError` or `IllegalArgumentException`); unrelated exception names fail. Source hashes, task contract, adapter, oracle, generator, and comparator are bound to the frozen protocol. Mixed tasks, duplicate IDs, unsupported envelope fields, and oversized inputs are rejected. Invalid scalar configuration values can still reach the oracle/candidate to test public error behavior.

CSV pruned feedback includes a bounded copy of the failing input as well as expected/actual observations. Retry memory remains optional, local to its trial/arm, and visible-only. The CSV task also uses the existing standard-library dependency policy, no-regression checkpoint selection, resource limits, and partitioned experiment budgets.

## Frozen suite

Profile: `commons-csv-v1`, pinned Commons CSV 1.10.0. SHA-256: `1dd4307ef5aa8683508991d07078cd81d29878d723b78ec45051de9a28a2ea3f`.

The suite contains **37 visible and 28 holdout scenarios**. Repeated Java reference executions matched. Each split contains both parse and print operations. Holdout inputs are separately authored compositions; normalized case payloads do not overlap. The fixed seed is recorded metadata, not a claim that this authored suite is a random sample.

Coverage includes quoted delimiters, doubled quotes, escaped characters, multiline fields, mixed line endings, empty records/fields, null markers, whitespace options, Unicode/NUL, custom delimiters/quotes, quote modes, exact printer separators, malformed quoted fields, and invalid configuration. Holdout scenarios combine these behaviors; they are not independent repositories and do not establish full API or branch coverage. The scope remains two behavioral entrypoints, not all public methods in the 12 vendored source files.

Frozen suite and validation audit: `evidence/20261118-csv-adapter-report/`. Evidence directory timestamps are UTC.

## Local qualification

- **125 Python tests pass**, including CSV task routing, schema/type checks, exact comparison, exception categories, input bounds, prompt isolation, split separation, and frozen-identity enforcement.
- Both Docker candidate images were rebuilt with the new adapter.
- The independent Python standard-library probe passes **33/37 visible scenarios per runtime**. It intentionally remains incomplete. Its four visible mismatches are surrounding-space handling and the ALL_NON_NULL, NONE, and custom-format printer cases.
- **8/8 injected defects are detected in both runtimes**: naive line/comma splitting, dropped empty fields, collapsed nulls, ignored trimming, reversed records, wrong exception category, LF-only printer output, and lost quote doubling.
- Detection counts only newly failing cases that the baseline probe passed. Infrastructure errors do not count as semantic detection. Qualification uses visible cases only.

Mutation evidence: `evidence/20261118T022637Z-csv-qualification-b4870d72/`. These are synthetic harness checks, not Gemini accuracy or proof that the baseline implements Commons CSV fully.

## Controller replay

A synthetic one-trial memory-on/off replay began with intentionally empty outputs, then supplied the same predetermined incomplete standard-library probe as the repair. One-shot scored **6/74 visible observations and 0/56 holdout** across both runtimes. Both repair arms selected the improved probe, scoring **66/74 visible and 44/56 holdout**. All three arms completed; none achieved full correctness. Exit code 1 therefore records negative candidate results, not an orchestration crash.

The audit confirmed identical paired initial candidates, selected-code hashes matching frozen selections, memory only in the enabled arm, no history in initial prompts, and no holdout case IDs in prompts or memory. The candidate was not adjusted using holdout results. This replay demonstrates orchestration and failure reporting; predetermined repairs cannot establish a benefit from memory.

Replay evidence: `evidence/20261118T022823Z-experiment-fbf0cc2a/`. **Zero model/API calls** were made.

## Commands and next step

From `midpoint/`, the frozen suite can be read from `evidence/20261118-csv-adapter-report/suite.json`. For a new suite path with the same current implementation:

```sh
python3 -m migration_lab freeze --task commons_csv --profile commons-csv-v1 \
  --seed 6158 --output runs/csv-new/suite.json
python3 scripts/qualify_csv.py --suite runs/csv-new/suite.json
python3 -m migration_lab experiment --backend replay \
  --replay-manifest fixtures/replay_csv.json --suite runs/csv-new/suite.json \
  --task commons_csv --trials 1 --max-repairs 1 --timeout 90 --memory-ablation --archive
```

The next step is an explicitly budgeted live Gemini smoke test. The source-only initial prompt is 210,127 UTF-8 bytes; a simple JSON-wrapped prompt plus the existing overhead allowance is 220,836 bytes before provider-specific fields. Candidate code and feedback add to that on retries. Measure the actual request and reserve enough capacity; the existing 272,000 input-allowance guard must not be bypassed. Context compaction may be necessary if generated candidates are large. No claim about live CSV translation performance is available yet.

CSV changes remain local and unpushed. CLI's completed push remains at `f0acd73`.

## Subsequent live checkpoint

The preparation checkpoint above preceded the completed [live CSV study](CSV_LIVE_OBSERVATIONS.md). Live smoke, three main trials, and three separate memory trials now have archived evidence. Code repair improved held-out case accuracy but no candidate passed the entire suite. Local history did not improve final accuracy. The CSV implementation and these observations are included in the subsequent CSV commit; the older local-only status above describes the preparation checkpoint.
