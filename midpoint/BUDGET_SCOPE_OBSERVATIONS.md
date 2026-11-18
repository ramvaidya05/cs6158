# Main-study budgeting and scope observations

Date: November 17, 2026. This checkpoint implements budget isolation and an executable scope audit. It does not expand the translation contract or run a new paid experiment.

## Why this change was necessary

The archived semantic-v2 study (`evidence/20261117T222306Z-experiment-f3578eff`) used a shared $1 reservation cap. Its fifth trial's operation-feedback repair was rejected before a model call, after other arms consumed the available budget. That trial cannot establish that operation feedback performed worse. The corrected report is in `evidence/20261117-semantic-v2-report`; the original archive remains unchanged.

The five-trial results remain one-shot 3/5, basic feedback 4/5, and operation feedback 4/5 full successes, with one budget-confounded paired comparison. These small-sample findings do not establish superiority of either repair strategy.

## Implemented budget policy

`experiment` now defaults to `--budget-policy partitioned`. Before creating experiment artifacts or making model requests, it checks whether the declared dollar cap can fund all planned call slots conservatively. Each trial has one initial-generation allocation and a separate allocation for each repair arm. Both repair arms reuse the same initial response without another initial-generation charge. Unused funds never transfer between arms or trials.

Each initial allocation funds one call; each repair allocation funds `max_repairs` calls. Envelopes use the existing maximum admitted input allowance of 272,000 tokens and the configured per-call output maximum. Failed calls with unknown usage retain their reservation. Known usage settles against its own allocation. The saved `spend.json` records allocation limits, costs, and each call's allocation. Existing output-token, time, and repair-count limits still apply: budget isolation does not guarantee successful translation or completion under those other limits.

At the previously supplied accounting rates ($0.75/M input, with the existing 1.25 input premium, and $3.75/M output), a 32,768-token call reserves at most $0.37788. Five trials with three repairs per arm require capacity for 35 calls, or **$13.2258**. This is conservative reservation capacity, not a predicted charge or verified current provider price. The previous study accounted for $0.680049375 across ten actual calls. No cap was automatically raised and no new live run was started.

`--budget-policy shared` remains available explicitly to reproduce the older protocol. Old archives are not relabeled as partitioned runs. Fair-budget runs must be analyzed separately. Unknown provider charges and supplied pricing assumptions retain the existing limitations of local accounting.

## Scope audit

Run from the repository root:

```sh
python3 midpoint/scripts/audit_cli_scope.py \
  --suite midpoint/evidence/20261117T222306Z-experiment-f3578eff/evaluation-suite.json \
  --output midpoint/evidence/20261117-budget-scope-audit/scope.json
```

The audit links case operations to archived Java reference traces, tracks types through returned object handles, and distinguishes scheduled operations from those reached before an exception. It records input and script hashes for reproducibility. It is an evaluator-only report; it does not feed holdout cases into model prompts.

- Pinned library: Commons CLI 1.9.0; four exposed classes, **15 method signatures and three constructor signatures**. Eighteen Java source files provide context; that is not eighteen translated modules.
- Visible: 36 scenarios; all 15 exposed methods have normal-return reference observations.
- Holdout: 20 scenarios; only 10 exposed methods have direct reference observations. `Option.getOpt`, `getLongOpt`, `hasArg`, `isRequired`, and `getValue` are not directly exercised there.
- Current candidate output is one Python module. OptionGroup's public API, HelpFormatter, Properties defaults, typed conversion, arbitrary object graphs, and full repository translation remain excluded.
- These counts measure reference API exercise, not candidate correctness, upstream overload coverage, or line/branch coverage. A void setter returning normally alone does not establish correct state mutation.

The plan's approximately 30–60 scored-method target is **not yet met**. All-visible API exercise should not be presented as complete semantic coverage, and current holdout results should not imply every exposed method was checked.

## Validation and next milestone

All 87 unit tests passed. New tests check rejection before artifact creation/model calls, isolation under either repair-arm order, unknown-cost retention, local settlement and persisted accounting, zero-repair allocations, rejection of reused budgets, and scope counts after exceptions and returned aliases. The archived-suite audit ran without model calls or Docker execution; this checkpoint does not claim a new live integration result.

Before the next main study:

1. Expand the coherent CLI slice toward the planned size (OptionGroup is a candidate), or explicitly revise and justify the smaller target. Extend adapters, contracts, dependency context, and validation together.
2. Add separately authored holdout observations for the five missing methods and qualify the expanded suite. Freeze it as a new version; do not alter the published v2 suite or pool the new scores with old results.
3. Predeclare equal repair limits and sufficient reservation capacity, then run the paired one-shot/code-only/environment-aware study. Keep feedback ablations distinct from the main comparison.
4. Check AlphaTrans artifact/version compatibility before claiming a matched baseline comparison. Repository-scale translation and cross-trial learning remain future work.
