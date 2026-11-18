# Commons CLI v3 live-study observations

## Predeclared protocol

This study uses the frozen `commons-cli-extended-v3` suite, SHA-256 `a8d5e510761d2c9532e451387581b91f934f4754a69205e0c5c1c0d3f52c2a19`: 32 exposed methods, five classes, 44 visible scenarios, and 28 holdout scenarios. CPython and GraalPy are evaluated separately. Counts across the two runtimes are correlated observations, not independent programs.

Phases run sequentially: one live smoke translation excluded from cohort statistics; three fresh main-study trials; then three fresh memory-ablation trials. Each trial shares its initial translation verbatim across its three arms. Main arms: one-shot, code repair, environment-aware repair. Memory arms: one-shot, pruned feedback without history, the same pruned feedback with arm-local history. The two studies answer different questions and use separate fresh cohorts. No lessons transfer across trials, arms, or studies.

Configuration: `gemini-3.8-flash`, low thinking, 32,768 maximum output tokens per request, 131,072 output-token allowance per arm, up to three repairs, 300-second model request timeout, 90-second execution timeout, and 1,200-second per-arm loop deadline. Early stopping and non-regressing checkpoint selection remain enabled. All selections freeze before cohort holdout scoring. No manual candidate edits or suite changes are allowed after generation starts.

Healthy containers are used throughout. Environment-aware repair can act only on its existing allowlisted infrastructure fault; if no such fault occurs, this cohort does not demonstrate a benefit from environment repair. The memory ablation alternates repair-arm order by trial. The main study retains its fixed historical order.

Accounting uses the previously supplied rates of $0.75/M input, the existing 1.25 input premium, and $3.75/M output. These are explicit experiment estimates, not verified current provider pricing or invoice amounts. Caps: $0.40 for smoke, $8.00 for each study ($16.40 combined). Each study preallocates $7.93548 in independent worst-case call envelopes before API requests. Unknown-cost failures retain their reservation; unused envelopes are not transferred. The cap is not expected spend.

Run using `scripts/run_cli_v3_study.py --phase smoke|main|memory --suite evidence/20261117-retry-memory-v3-report/suite.json`, with the local key loaded without shell evaluation or credential logging. Model code runs only in Docker. Full artifacts are archived even for failed runs. Local replay evidence remains separate and is not counted as live inference.

## Results

Smoke completed successfully: 88/88 visible observations and 56/56 holdout observations across the two runtimes, from one model call. Archive: `evidence/20261118T002250Z-cli-v3-smoke-05baa037`. This run is excluded from the cohorts.

Main study completed: one-shot, code repair, and environment-aware repair each passed 3/3 task trials. Each arm scored 264/264 visible and 168/168 holdout observations across both runtimes. All initial candidates passed, so there were no repair calls or environment actions. Three actual model calls were made, not nine independent generations. Archive: `evidence/20261118T002418Z-cli-v3-main-e1839f4c`.

This main cohort provides no evidence of repair improvement: it has no initial failures to repair and no infrastructure faults. The result is test-supported parity on this slice, not full repository equivalence.

The separate memory cohort completed with one-shot **1/3 fully passing trials**, memory-off **3/3**, and memory-on **3/3**. Full success requires both visible and holdout checks to pass in both runtimes. Archive: `evidence/20261118T003004Z-cli-v3-memory-8ca90532`.

- Trial 1: initial 74/88 visible, 56/56 holdout. Both arms reached 88/88 visible and 56/56 holdout after one repair.
- Trial 2: initial 66/88 visible, 48/56 holdout. Both arms reached 88/88 visible and 56/56 holdout after one repair.
- Trial 3: initial 88/88 visible, 56/56 holdout. Neither arm needed repair.

Across this cohort, one-shot scored 228/264 visible observations and 160/168 holdout observations. Each repair arm scored 264/264 visible and 168/168 holdout. Per runtime, the holdout totals are 80/84 for one-shot and 84/84 for each repair arm. The two runtimes agree; combining them doubles observations, not independent evidence.

Visible full-pass counts after allowing 0, 1, 2, and 3 retries were 1/3, 3/3, 3/3, and 3/3 for both repair conditions. These are observed trajectory counts with successful checkpoints retained, not separate reruns at each budget. No second or third repair was needed. Holdout was scored only for final selections, not used to choose a retry budget.

## Observed failure mechanisms

Post-run source inspection found missing null/base-case handling while translating overloaded lookups:

- Trial 1's `CommandLine.getOptionValues()` recursively called itself with the unresolved `None` result. Both repairs added a `None` termination case; memory-off also explicitly checked the resolved result before delegation.
- Trial 2's `CommandLine.hasOption()` recursively delegated the unresolved result to itself without a `None` base case. The expected absent-option result was `False`; the observed result was `RecursionError`. Both repair arms corrected the visible failures in one retry.

This analysis was performed after generation; it was not inserted into model prompts. Trial-local machine-generated histories record observations and code-revision excerpts rather than claiming inferred root causes.

## Interpretation and limitations

These two failing initial translations support the usefulness of visible execution feedback and bounded repair on this slice. **They do not establish an additional benefit from retry memory**: memory-on and memory-off had identical correctness and retry counts, and neither needed a second retry where accumulated unsuccessful fixes might become more useful. The history feature worked, but its comparative value remains unproven. Three trials per study and one library slice are too small for a broad generalization claim.

Do not compare the main cohort's perfect one-shot results with the memory cohort's initial failures as a treatment effect: they are separate fresh samples. Within each cohort, all arms shared their initial code and settings. Sampling controls not explicitly set by the backend used provider defaults; all calls resolved to `gemini-3.8-flash`.

The first memory trial's original candidate passed all holdout cases despite failing visible absent-value lookups. Therefore, 32/32 methods exercised is not complete behavioral coverage. Preserve these results and this frozen suite; a future suite should independently test absent `getOptionValues()`/`getOptionValue()` paths and their interaction with parser state. Any such addition is a new protocol, not a retrospective correction of this study's scores.

## Cost and integrity

Eleven actual Gemini calls: one smoke, three main-study initial generations, and seven memory-study calls (three initials plus four repairs). Initial reuse did not make additional API requests. No environment actions, unknown-usage calls, or budget-blocked arms occurred.

Conservative accounted costs: smoke $0.06487875; main study $0.19756125; memory study $0.496186875; combined **$0.758626875**. These estimates use the declared rates, not a provider invoice. Both studies stayed well below their independent reservation caps.

The artifact audit confirmed identical initial candidates within each trial, selected-code hashes matching frozen selections, memory documents only in memory-enabled arms, no holdout case IDs in prompts/history, and no configured API key in any archived file. Structured report and audit: `evidence/20261118-cli-v3-live-report/summary.json`. Raw results remain in the three phase archives listed above.

## Next work

The scoped CLI live studies are now executed and documented. Remaining research work is to add the newly identified semantic holdout strata in a separately versioned suite, investigate source-guided handling of overloaded nullable lookups, and evaluate memory on tasks that naturally require multiple unsuccessful revisions. The matched AlphaTrans comparison and multi-module/repository translation remain outside this completed cohort. Keep memory as an optional treatment; the present results do not justify claiming it is superior.
