# Failure taxonomy for the final report

The controller routes failures using observed execution status and typed comparisons. The mechanisms below come from inspecting the corresponding source, candidates and traces. The observations support a small set of concrete categories. Frequency estimates would require labeling every archived trial under a common protocol.

## Translation and compatibility failures

- **Overload resolution and missing values (CLI).** A missing option resolves to Java `null`. In CLI v3 memory trial 1, `getOptionValues()` recursively called itself on the unresolved `None` and raised `RecursionError`. Trial 2 repeated the pattern in `hasOption()`, which should return `False` for an absent option. Both repair conditions fixed both candidates within one retry. The first candidate passed the old holdout despite its visible failures. [CLI evidence](CLI_V3_LIVE_OBSERVATIONS.md).
- **Lexical semantics and character units (CSV).** An escaped delimiter belongs to the current field, and `\\n` in an escape-enabled field becomes a newline without ending the record. A supplementary character such as `🚀` occupies two Java UTF-16 units and is invalid as a one-unit delimiter. CSV v1 selected repairs retained these holdout failures despite strong visible scores. CSV v2 moved inspected cases into development, added Java-source guidance and passed the new holdout after one retry per repaired candidate. The v2 changes were bundled. [CSV v1](CSV_LIVE_OBSERVATIONS.md) · [CSV v2](CSV_V2_OBSERVATIONS.md).
- **Unicode API portability (Codec and Validator).** The selected Codec Hex live continuation passed 110/110 CPython and 108/110 GraalPy holdout cases. Validator Luhn's first proposed repair improved CPython visible from 28/30 to 30/30 and dropped GraalPy to 10/30 through reliance on `unicodedata.decimal`, unavailable in the pinned GraalPy runner. The checkpoint gate rejected it. Assisted Java-derived conversion subsequently passed the inspected regression suites. [Codec](CODEC_V2_OBSERVATIONS.md) · [Validator](VALIDATOR_OBSERVATIONS.md).
- **Surrogate failure and cross-split regression (Validator).** In paired diagnosis trial 2 a repair passed all 30 visible cases in both runtimes, yet GraalPy holdout fell from 135/136 to 133/136. Three isolated-surrogate inputs raised exceptions where `isValid` should return false. A visible non-regression gate protects known visible behavior only. [Paired diagnosis evidence](PAIRED_DIAGNOSIS_OBSERVATIONS.md).
- **Numeric semantics (Jaro-Winkler).** The synthetic fractional-transposition defect escaped the original visible cases but was detected by withheld cases. This is evaluator sensitivity evidence. [Mutation results](EXPERIMENT_RESULTS.md#november-13-continued-trials-and-evaluator-sensitivity).

## Execution and experimental failures

- **Runtime setup.** Trusted GraalPy preflight failed after an intentionally unwritable cache path was introduced. The controller routed the failure to its allowed environment action and recovered execution. The routing experiment also checked candidate syntax, candidate exceptions and semantic mismatches in healthy containers, matching all 10 expected observations. [Routing evidence](evidence/20261117T223101Z-failure-routing-dece3254/summary.json).
- **Incomplete generation.** Validator factorial request 3 ended at `MAX_TOKENS`; 3,440 of its 4,078 output tokens were thinking tokens. The study stopped without scoring any matched holdout comparisons. Provider HTTP errors and timeouts similarly require separate operational accounting when no usable candidate exists. [Factorial attempt](FACTORIAL_DIAGNOSIS_PROTOCOL.md).
- **Run integrity.** A historical run changed a protected test file mid-run and was invalidated. Freeze suite and oracle identities before scored generation and keep invalidated evidence in the run history. [Reviewer follow-up](REVIEWER_RESPONSE.md).

## Representative resource use

Costs are accounting estimates at the rates documented for each study. Timing boundaries differ by study, so these values describe overhead rather than rank performance.

- Validator first pilot used 7,596 tokens and 38.122 seconds. Its guided continuation used 5,459 tokens and 31.602 seconds. Neither replaced the original checkpoint.
- Fresh paired Validator diagnosis used 35,225 tokens over nine calls and 188.307 seconds including preparation, probe execution and scoring. Two of three diagnosis selections passed the full suite.
- The incomplete Validator factorial batch used 13,893 tokens over three calls in 53.689 seconds. These resources produced no completed comparison.
- CSV v2 used 222,847 input and 59,921 output tokens across nine calls. Every repair arm passed after one retry. [Archived aggregate](evidence/20261121T232749Z-csv-v2-main-d4aa60a3/summary.json).
- CLI v3 memory trial 1's original request used 40,716 input and 7,887 output tokens. Its memory-off repair used another 50,991 input and 7,913 output tokens. The repair arm elapsed 68.367 seconds including evaluation and with the initial response reused. [Trial artifacts](evidence/20261118T003004Z-cli-v3-memory-8ca90532/trial-000/commons_cli/memory_off/result.json).
