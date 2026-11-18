# Commons CSV preparation

Date: November 17, 2026 (America/New_York).

## CLI handoff

CLI implementation, semantic-v2/v3 evidence, retry memory, budget isolation, and live observations were committed as `c0939af`. Newer origin reporting and Codec studies were preserved in merge `f0acd73`, pushed successfully to `origin/main`. Merge validation passed 113 Python tests, a clean Java build with five tests, and a read-only check that dynamic memory-arm reporting retained archived scores. Archived experiment logs were not rewritten to remove whitespace.

The abandoned local Codec 1.17.1 preparation was moved to ignored `.cache/paused-codec-1.17.1`. The collaborator's tracked Codec 1.22.1 work remains intact. CSV is the next subject selected by the user.

## Source and initial scope

Pinned artifact: `org.apache.commons:commons-csv:1.10.0`. This is an intentional fixed historical version, not a claim about the latest release or a matched AlphaTrans version. The source archive was fetched from Maven Central, matched against its published SHA-1, and recorded with a local SHA-256 plus per-file SHA-256 hashes. All 12 Java package source files are vendored unchanged, with Apache LICENSE and NOTICE preserved. Their imports are Java standard-library or same-package imports; the CSV source build adds no external runtime dependency.

The proposed first slice exposes two behavioral entrypoints: parse text into records and print text/null records into CSV. It includes configurable delimiter, quote/escape characters, record separator, null marker, quote mode, trimming, and empty-line/surrounding-space behavior. The adapter uses `CSVFormat.DEFAULT` as its base. Exact field values, field order, embedded newlines, and printer line endings matter.

This is **two proposed observable entrypoints**, not 12 translated classes or full repository migration. Headers/name-based lookup, file/network/JDBC I/O, arbitrary-object printing, streaming lifecycle, and unrestricted presets are initially excluded. `benchmarks/commons_csv.json` is explicitly a draft contract, not a frozen evaluation suite.

## Work completed

- Vendored source and provenance: `vendor/commons-csv/SOURCE.json`.
- Added the source directory to the Java build.
- Added `CsvScenario.java`, an evaluator-owned parse/print oracle reachable through the Java harness's `commons_csv` reference branch.
- Added five harness-owned Java qualification tests covering boundary behavior: quoted commas/multiline/empty fields, printer escaping and CRLF, unterminated quotes, format settings/null markers, and invalid option types. These are not upstream tests or translated-code accuracy results.
- Added `scripts/qualify_csv_source.py`, which verifies pinned source hashes and repeats eight development scenarios against the Java oracle.

I/O parsing failures are normalized to `CSVParseError`; invalid configuration/input shapes are reported as `IllegalArgumentException`. Exception messages are not part of the proposed comparison. Configuration types are checked explicitly rather than coerced silently.

## Validation

Clean Java build: ten tests passed (five existing plus five CSV qualification tests). The eight development oracle scenarios produced identical rows in two executions. Evidence: `evidence/20261118T021847Z-csv-source-qualification-676da983` (directory timestamp is UTC). No Gemini requests, Python candidate evaluations, or CSV accuracy claims were made.

Python regression suite: 113 tests passed. CSV-specific candidate tests are not yet implemented.

## Next implementation milestone

1. Add a strict Python candidate protocol and both CPython/GraalPy execution adapters for the two entrypoints; do not reuse the numeric comparator.
2. Define exact nested-list/string/exception comparison and qualify it with deliberately wrong quoting, newline, whitespace, null-marker, and escaping implementations.
3. Author visible and independently composed holdout scenarios, including malformed inputs and parse/print composition. Freeze a new CSV-only protocol before live generation.
4. Assemble source-only model context. The raw package source is 209,118 bytes, so repair context plus candidate code could approach the current 272,000-byte-derived input allowance. Measure and bound context before choosing live settings; preserve source hashes for any deterministic context extraction.
5. Rebuild the candidate Docker images after adapter changes, complete replay validation, then run an explicitly budgeted Gemini smoke and paired study. Keep results separate from CLI and the collaborator's Codec results.

The Java oracle is ready for development. CSV is not yet registered as a runnable end-to-end translation task. Historical CLI suites remain tied to their recorded evaluator versions; reproducing archived results requires the matching source version, rather than silently accepting changed harness fingerprints.


## Subsequent implementation

The candidate adapters, exact comparator, frozen CSV-only suite, mutation checks, and controller replay are now implemented. See [CSV_ADAPTER_OBSERVATIONS.md](CSV_ADAPTER_OBSERVATIONS.md) for the current checkpoint; the preparation status above records the earlier milestone. No paid CSV calls have been made.
