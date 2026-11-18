# Translation failure history

Scope: this trial/arm only. Visible observations, not verified causal lessons. Rejected revisions are recorded but must not replace the selected checkpoint. Do not repeat failed revisions; preserve passing behavior. No holdout information.

## Attempt 0 — visible_failures_remain
```json
{
  "attempt": 0,
  "candidate_sha256": "cee9e68062c8dc2574d3ca0ba0e6564b688e550ac1e30028de1ca0c474a67c7a",
  "accepted_checkpoint": true,
  "verification": "visible_failures_remain",
  "diagnostics": {
    "passed": 70,
    "total": 74,
    "groups_total": 2,
    "failures": [
      {
        "id": "a9d1bb58d92be1ea",
        "category": "runtime_exception",
        "expected": "{\"id\": \"csv-v1-visible-escaped-quote\", \"status\": \"ok\", \"value\": [[\"a\\\"b\", \"c\"]]}",
        "actual": "{\"id\": \"csv-v1-visible-escaped-quote\", \"status\": \"exception\", \"type\": \"TypeError\"}",
        "input": "{\"config\": {\"escape\": \"\\\\\"}, \"operation\": \"parse\", \"text\": \"\\\"a\\\\\\\"b\\\",c\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-escaped-quote"
        ]
      },
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
  "candidate_sha256": "dce51a86f363dfb59406e598968e4f8b1e6d11f8f2d4a7e9ca5ddeddf66681a7",
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
      "case_id": "csv-v1-visible-escaped-quote"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-escaped-quote"
    },
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-invalid-bool"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-invalid-bool"
    }
  ],
  "attempted_revision_excerpt": "--- selected-checkpoint.py\n\n+++ attempt-candidate.py\n\n@@ -18,10 +18,4 @@\n\n     NON_NUMERIC = \"NON_NUMERIC\"\n     NONE = \"NONE\"\n-\n-\n-class DuplicateHeaderMode(Enum):\n-    ALLOW_ALL = \"ALLOW_ALL\"\n-    ALLOW_EMPTY = \"ALLOW_EMPTY\"\n-    DISALLOW = \"DISALLOW\"\n \n \n@@ -73,4 +67,13 @@\n\n \n \n+def _check_bool(config: Dict[str, Any], key: str, default: bool) -> bool:\n+    if key not in config:\n+        return default\n+    val = config[key]\n+    if not isinstance(val, bool):\n+        raise IllegalArgumentException(f\"{key} must be a boolean\")\n+    return val\n+\n+\n def _build_format(config: Optional[Dict[str, Any]]) -> _CSVFormat:\n     if config is None:\n@@ -111,8 +114,8 @@\n\n             raise IllegalArgumentException(\"quote_mode must be string or QuoteMode\")\n \n-    ignore_empty_lines = bool(config.get(\"ignore_empty_lines\", True))\n-    ignore_surrounding_spaces = bool(config.get(\"ignore_surrounding_spaces\", False))\n-    trim = bool(config.get(\"trim\", False))\n-    trailing_delimiter = bool(config.get(\"trailing_delimiter\", False))\n+    ignore_empty_lines = _check_bool(config, \"ignore_empty_lines\", True)\n+    ignore_surrounding_spaces = _check_bool(config, \"ignore_surrounding_spaces\", False)\n+    trim = _check_bool(config, \"trim\", False)\n+    trailing_delimiter = _check_bool(config, \"trailing_delimiter\", False)\n \n     return _CSVFormat(\n@@ -242,5 +245,5 @@\n\n             return True\n         ahead = self.reader.look_ahead(len(self.delimiter) - 1)\n-        if len(ahead) < len(self.delimiter) - 1:\n+        if not isinstance(ahead, list) or len(ahead) < len(self.delimiter) - 1:\n             return False\n         for i in range(len(ahead)):\n@@ -255,5 +258,5 @@\n\n         needed_len = 2 * len(self.delimiter) - 1\n         ahead = self.reader.look_ahead(needed_len)\n-        if len(ahead) < needed_len:\n+        if not isinstance(ahead, list) or len(ahead) < needed_len:\n             return False\n         if ahead[0] != self.delimiter[0]:\n@@ -285,5 +288,5 @@\n\n \n     def read_end_of_line(self, ch: int) -> bool:\n-        if ch == 13 and self.reader.look_ahead() == 10:\n+        if ch == 13 and self.reader.look_ahead(1) == 10:\n             self.reader.read()\n             return True\n@@ -379,5 +382,5 @@\n\n                         token.content.append(chr(unescaped))\n             elif self.is_quote_char(c):\n-                if self.is_quote_char(self.reader.look_ahead()):\n+                if self. \u2026 [truncated; see raw evidence]"
}
```
