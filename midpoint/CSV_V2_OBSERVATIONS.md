# CSV v2 completion work

Updated November 21, 2026 (America/New_York).

## Scope and changes

The goal is to complete the existing Commons CSV 1.10.0 parser/printer slice, not claim full-library migration. The v1 evidence and scores remain unchanged. Its now-inspected 65 visible/holdout cases are all development cases in v2, supplemented by escape, character-validation, and whitespace regressions (101 total). A new 59-case holdout combines different values, delimiters, escape characters, null/quote modes, whitespace, malformed records, and configuration errors. This is independently authored confirmation coverage, not exhaustive equivalence.

`csv_context.py` removes comments/blank lines deterministically while preserving executable Java and literals. A source-grounded checklist points the model to Lexer escape processing, CSVParser null handling, Java UTF-16 configuration validation, whitespace distinctions, and exact printer behavior. It contains no case IDs, expected outputs, or prior generated candidate code. The prompt shrank from approximately 210 KB to 72,755 UTF-8 bytes. This is context compaction and semantic guidance, not dynamic retrieval, a dependency graph, or cross-project memory.

`commons-csv-v2` binds the new generator and context code into its frozen identity. Old archives must be reproduced at their recorded commits; fingerprints are not rewritten to make old protocols appear current. Java source, oracle adapters, comparator, and candidate isolation are unchanged.

## Predeclared live validation

Freeze v2 with seed 6158 after repeated Java oracle agreement. Run three fresh paired trials with Gemini `gemini-3.8-flash`, low thinking. Arms: one-shot, code repair, environment-aware repair. Reuse each trial's initial candidate verbatim; no hand-edited translations. Up to three repairs, 32,768 output tokens/request, 131,072 output tokens/arm, 300s model timeout, 90s runtime timeout, 1,200s arm deadline. Stop on success, repeated candidates, non-progress, or limits. Memory remains off. All selections freeze before holdout scoring; no candidate or prompt tuning against this new holdout.

One $8 cohort cap, partitioned before calls; accounting assumptions remain $0.75/M input with 1.25 premium and $3.75/M output, not verified invoice prices. No separate paid smoke or memory study is planned. Healthy containers provide no planned environment-repair opportunity. Acceptance requires every development and holdout case to pass in both runtimes; failures will be reported rather than removed or relabeled.

This tests the combined new context and development coverage. Comparing it with historical v1 does not isolate the causal effect of context compaction or guidance. Three trials do not establish broad generality.

## Validation and results

- 129 Python unit tests pass, including promotion/disjointness, literal-safe context compaction, prompt isolation, and v2 frozen identity.
- Existing pinned Java build verifies; no Java changes were made. All 12 compacted source files also compile with javac against the pinned dependencies.
- Development-only evaluation of a saved v1 repaired candidate passed 89/101 cases per runtime, exposing 12 failures (escaped delimiters, supplementary character settings, and nonbreaking-space handling). No new API call or holdout scoring was used for this qualification. Archive: `evidence/20261121T232733Z-csv-v2-development-check-42b720d6`.

## Live results

The frozen suite SHA-256 is `e13be5ca15628267df04222cbf21fe18240a37709ca8a864f76689e9d6905764`. Run date: November 21, 2026 (America/New_York). Gemini `gemini-3.8-flash` made nine live calls at an estimated cost of $0.4336228125 under the declared accounting rates. Every call recorded usage.

- One-shot development scores were 98/101, 100/101, and 98/101. Holdout scores were 56/59, 59/59, and 56/59. Full-suite success was 0/3.
- Code repair and environment-aware repair each achieved 3/3 full-suite passes. Every repaired selection passed 101/101 development and 59/59 holdout cases in each runtime after one retry.
- No environment actions occurred. The two runtimes agreed on case counts. Both runtimes tested the same candidates, so each arm still represents three trials.

The verified Python module exposes `parse_csv(text, config)` and `print_csv(records, config)`. See the [trial 1 code-repair selection](evidence/20261121T232749Z-csv-v2-main-d4aa60a3/trial-000/commons_csv/code_repair/final.py) and its [selection record](evidence/20261121T232749Z-csv-v2-main-d4aa60a3/trial-000/commons_csv/code_repair/selection.json). The selected file is the archived model output. Headers, named lookup, and full-library migration remain outside the scoped milestone.

The audit verified identical initial candidates within each trial, final file hashes, no holdout case IDs in prompts, no retry-memory files, no configured credential values in evidence, and archive checksums. See the [audit summary](evidence/20261121-csv-v2-report/summary.json). This cohort evaluates the updated workflow as a whole.
