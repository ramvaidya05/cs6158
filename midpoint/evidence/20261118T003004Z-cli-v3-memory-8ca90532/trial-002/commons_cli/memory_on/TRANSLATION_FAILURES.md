# Translation failure history

Scope: this trial/arm only. Visible observations, not verified causal lessons. Rejected revisions are recorded but must not replace the selected checkpoint. Do not repeat failed revisions; preserve passing behavior. No holdout information.

## Attempt 0 — all_visible_pass
```json
{
  "attempt": 0,
  "candidate_sha256": "fc6994cb7d3cd37d1a81d495cd9b4f998fe6b148190bc143aaa4095762797034",
  "accepted_checkpoint": true,
  "verification": "all_visible_pass",
  "diagnostics": {
    "passed": 88,
    "total": 88,
    "groups_total": 0,
    "failures": [],
    "note": "Observations only, not inferred root causes. Full details remain in visible/summary.json."
  },
  "fix_status": "Code revision evaluated; causal explanation not established",
  "evidence": "attempts/00/visible/summary.json",
  "previously_failing_observations_now_passing": []
}
```
