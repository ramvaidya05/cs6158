# Translation failure history

Scope: this trial/arm only. Visible observations, not verified causal lessons. Rejected revisions are recorded but must not replace the selected checkpoint. Do not repeat failed revisions; preserve passing behavior. No holdout information.

## Attempt 0 — visible_failures_remain
```json
{
  "attempt": 0,
  "candidate_sha256": "d3313691c23b07966fc45aef1aef71871dfdbe03996016b9951053b3c2cee306",
  "accepted_checkpoint": true,
  "verification": "visible_failures_remain",
  "diagnostics": {
    "passed": 70,
    "total": 74,
    "groups_total": 2,
    "failures": [
      {
        "id": "da5cfb04151a8cf7",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-invalid-bool\", \"status\": \"exception\", \"type\": \"IllegalArgumentException\"}",
        "actual": "{\"id\": \"csv-v1-visible-invalid-bool\", \"status\": \"ok\", \"value\": [[\"a\"]]}",
        "input": "{\"config\": {\"trim\": 1}, \"operation\": \"parse\", \"text\": \"a\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-invalid-bool"
        ]
      },
      {
        "id": "6ec764c9f96c9317",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-invalid-quote-mode\", \"status\": \"exception\", \"type\": \"IllegalArgumentException\"}",
        "actual": "{\"id\": \"csv-v1-visible-invalid-quote-mode\", \"status\": \"ok\", \"value\": [[\"a\"]]}",
        "input": "{\"config\": {\"quote_mode\": \"UNKNOWN\"}, \"operation\": \"parse\", \"text\": \"a\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-invalid-quote-mode"
        ]
      }
    ],
    "note": "Observations only, not inferred root causes. Full details remain in visible/summary.json."
  },
  "fix_status": "Code revision evaluated; causal explanation not established",
  "evidence": "attempts/00/visible/summary.json",
  "previously_failing_observations_now_passing": []
}
```

## Attempt 1 — all_visible_pass
```json
{
  "attempt": 1,
  "candidate_sha256": "c123872bd5846c0b9382090fa1f121d1f80178a84449673ae7209a31f7df8e2d",
  "accepted_checkpoint": true,
  "verification": "all_visible_pass",
  "diagnostics": {
    "passed": 74,
    "total": 74,
    "groups_total": 0,
    "failures": [],
    "note": "Observations only, not inferred root causes. Full details remain in visible/summary.json."
  },
  "fix_status": "Code revision evaluated; causal explanation not established",
  "evidence": "attempts/01/visible/summary.json",
  "previously_failing_observations_now_passing": [
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-invalid-bool"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-invalid-bool"
    },
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-invalid-quote-mode"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-invalid-quote-mode"
    }
  ],
  "attempted_revision_excerpt": "--- selected-checkpoint.py\n\n+++ attempt-candidate.py\n\n@@ -24,4 +24,6 @@\n\n UNDEFINED = -2\n DISABLED = \"\\ufffe\"\n+\n+VALID_QUOTE_MODES = {\"ALL\", \"ALL_NON_NULL\", \"MINIMAL\", \"NON_NUMERIC\", \"NONE\"}\n \n \n@@ -142,4 +144,12 @@\n\n     def __init__(self, config=None):\n         cfg = config or {}\n+        if not isinstance(cfg, dict):\n+            raise IllegalArgumentException(\"Config must be a dictionary\")\n+\n+        self._validate_type(cfg, \"ignore_empty_lines\", bool)\n+        self._validate_type(cfg, \"ignore_surrounding_spaces\", bool)\n+        self._validate_type(cfg, \"trim\", bool)\n+        self._validate_type(cfg, \"trailing_delimiter\", bool)\n+\n         self.delimiter = cfg.get(\"delimiter\", \",\")\n         self.quote_character = cfg.get(\"quote\", '\"')\n@@ -154,4 +164,10 @@\n\n         self.comment_marker = cfg.get(\"comment_marker\", None)\n \n+        if self.quote_mode is not None and self.quote_mode not in VALID_QUOTE_MODES:\n+            raise IllegalArgumentException(f\"Invalid quote_mode: {self.quote_mode}\")\n+\n+        self._validate_types(cfg)\n+        self.validate()\n+\n         if self.quote_character is not None and self.null_string is not None:\n             self.quoted_null_string = f\"{self.quote_character}{self.null_string}{self.quote_character}\"\n@@ -159,5 +175,30 @@\n\n             self.quoted_null_string = None\n \n-        self.validate()\n+    def _validate_type(self, cfg, key, expected_type):\n+        if key in cfg and cfg[key] is not None:\n+            if not isinstance(cfg[key], expected_type):\n+                raise IllegalArgumentException(f\"{key} must be of type {expected_type.__name__}\")\n+\n+    def _validate_types(self, cfg):\n+        if \"delimiter\" in cfg:\n+            val = cfg[\"delimiter\"]\n+            if val is None or not isinstance(val, str):\n+                raise IllegalArgumentException(\"delimiter must be a non-null string\")\n+        if \"quote\" in cfg:\n+            val = cfg[\"quote\"]\n+            if val is not None and not isinstance(val, str):\n+                raise IllegalArgumentException(\"quote must be a character or null\")\n+        if \"escape\" in cfg:\n+            val = cfg[\"escape\"]\n+            if val is not None and not isinstance(val, str):\n+                raise IllegalArgumentException(\"escape must be a character or null\")\n+        if \"record_separator\" in cfg:\n+            val = cfg[\"record_separator\"]\n+            if val is not None and not i \u2026 [truncated; see raw evidence]"
}
```
