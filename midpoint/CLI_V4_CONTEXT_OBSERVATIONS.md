# Commons CLI v4 coverage and context comparison

CLI v4 keeps the same Commons CLI 1.9.0 interface and 32-method contract. The development set contains all 72 scenarios from v3 plus three nullable-lookup regressions. Fourteen fresh holdout scenarios combine missing options, absent optional values, populated lookups and repeated parser calls. Tests inspect results retained by earlier `CommandLine` objects after later parses. The new holdout specifically probes missing-value behavior. The complete v3 suite remains available for historical comparability.

Frozen suite SHA-256: `7a6e6f5ec0bcc57890873eb510b33f0ef962203a6527061af1308804abf19a6a`. The reference was executed twice with identical results before generation. A coverage audit replayed two previously archived candidates in Docker. The original candidate scored 5/14 per runtime. Its repaired counterpart scored 14/14 per runtime. The old v3 holdout had passed the original candidate on all 28 scenarios. See [coverage evidence](evidence/20261123T163241Z-cli-v4-coverage-db6d3b09/summary.json).

## Study design

Three blocks each make two independent one-shot requests. One uses the existing full source prompt. The other removes source comments and blank lines while preserving literals, and adds source-based guidance about nullable overloads, cloning and parser reuse. The prompts are 164,054 and 58,811 UTF-8 bytes, a 64.15% reduction. The comparison estimates the combined effect of compaction and semantic guidance. Each block uses both conditions in alternating order. There is no matching by random seed or reuse of generated code.

Both conditions use Gemini 3.8 Flash with low thinking, one call per candidate, a 32,768 output-token allowance, and the same frozen evaluator. Each call has an independent $0.38 accounting cap at the project's declared rates. The six-call cap is $2.28. Generated code executes in pinned CPython and GraalPy images. The runner scores holdout after all generation attempts and checkpoint selections. Full-suite success requires every development and holdout scenario to pass in both runtimes. Token totals and elapsed time are secondary endpoints. Neither prompt includes evaluation scenarios or expected results.

## Reproduce

From `midpoint/` after Java bootstrap and container build:

```sh
python3 -m migration_lab freeze --task commons_cli --profile commons-cli-lookup-v4 --seed 6158 --output runs/cli-v4-preparation/suite.json
python3 scripts/run_cli_context_study.py --suite runs/cli-v4-preparation/suite.json
```

The second command makes paid requests. Use a new output path for each freeze. Archived fingerprints bind the study to its evaluator revision.

## Observed results

[Live archive and per-run metrics](evidence/20261123T163218Z-cli-v4-context-4b9c4021/summary.json). Full-suite passes were 1/3 with full context and 2/3 with compact guided context. The compact arm used 60.6% fewer input tokens.

- **full** achieved 1/3 full-suite passes. 3/3 reached final scoring. Total recorded input/output tokens were 122,148/22,532, accounted cost was $0.199009, and summed arm time was 219.78 seconds including scoring.
  - Block 1. Development cpython 75/75 (completed), graal 75/75 (completed). Holdout cpython 14/14 (completed), graal 14/14 (completed).
  - Block 2. Development cpython 59/75 (completed), graal 59/75 (completed). Holdout cpython 10/14 (completed), graal 10/14 (completed).
  - Block 3. Development cpython 59/75 (completed), graal 59/75 (completed). Holdout cpython 10/14 (completed), graal 10/14 (completed).
- **compact_guided** achieved 2/3 full-suite passes. 3/3 reached final scoring. Total recorded input/output tokens were 48,123/21,770, accounted cost was $0.126753, and summed arm time was 201.40 seconds including scoring.
  - Block 1. Development cpython 0/75 (syntax_error), graal 0/75 (syntax_error). Holdout cpython 0/14 (syntax_error), graal 0/14 (syntax_error).
  - Block 2. Development cpython 75/75 (completed), graal 75/75 (completed). Holdout cpython 14/14 (completed), graal 14/14 (completed).
  - Block 3. Development cpython 75/75 (completed), graal 75/75 (completed). Holdout cpython 14/14 (completed), graal 14/14 (completed).

Pooled holdout scores per runtime were 34/42 for full context and 28/42 for compact guidance. The compact arm produced more completely correct candidates and fewer passing case observations overall.

The first compact candidate contained an unclosed parenthesis at line 279. Its syntax failure remains in the denominator. The protocol scheduled one generation per arm per block. Three trials per arm provide a descriptive comparison on the scoped API.

Archive checksums and selected-code hashes verified. Holdout IDs were absent from archived prompts, and the archives contained no configured credential values. All 145 unit tests passed after the changes.
