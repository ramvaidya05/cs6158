# Translation failure history

Scope: this trial/arm only. Visible observations, not verified causal lessons. Rejected revisions are recorded but must not replace the selected checkpoint. Do not repeat failed revisions; preserve passing behavior. No holdout information.

## Attempt 0 — visible_failures_remain
```json
{
  "attempt": 0,
  "candidate_sha256": "2c8b6ce71a51dcd4283cabaee87b3dc717bf6ed544460886add9ce6f7abb33d1",
  "accepted_checkpoint": true,
  "verification": "visible_failures_remain",
  "diagnostics": {
    "passed": 6,
    "total": 74,
    "groups_total": 34,
    "failures": [
      {
        "id": "c2fa88242c2765aa",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-blank-kept\", \"status\": \"ok\", \"value\": [[\"a\"], [\"\"]]}",
        "actual": "{\"id\": \"csv-v1-visible-blank-kept\", \"status\": \"ok\", \"value\": []}",
        "input": "{\"config\": {\"ignore_empty_lines\": false}, \"operation\": \"parse\", \"text\": \"a\\n\\n\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-blank-kept"
        ]
      },
      {
        "id": "ceb8269242d71021",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-trailing-fields\", \"status\": \"ok\", \"value\": [[\"a\", \"\", \"\"], [\"b\", \"c\", \"\"]]}",
        "actual": "{\"id\": \"csv-v1-visible-trailing-fields\", \"status\": \"ok\", \"value\": []}",
        "input": "{\"config\": {}, \"operation\": \"parse\", \"text\": \"a,,\\nb,c,\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-trailing-fields"
        ]
      },
      {
        "id": "57b4a9b5bc949183",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-quoted-empty\", \"status\": \"ok\", \"value\": [[\"\", \"x\"]]}",
        "actual": "{\"id\": \"csv-v1-visible-quoted-empty\", \"status\": \"ok\", \"value\": []}",
        "input": "{\"config\": {}, \"operation\": \"parse\", \"text\": \"\\\"\\\",x\\n\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-quoted-empty"
        ]
      },
      {
        "id": "474c2afb9ada2a69",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-quoted-delimiter\", \"status\": \"ok\", \"value\": [[\"a\", \"b,c\"]]}",
        "actual": "{\"id\": \"csv-v1-visible-quoted-delimiter\", \"status\": \"ok\", \"value\": []}",
        "input": "{\"config\": {}, \"operation\": \"parse\", \"text\": \"a,\\\"b,c\\\"\\n\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-quoted-delimiter"
        ]
      },
      {
        "id": "9261d79d5545770f",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-doubled-quote\", \"status\": \"ok\", \"value\": [[\"say \\\"hi\\\"\", \"end\"]]}",
        "actual": "{\"id\": \"csv-v1-visible-doubled-quote\", \"status\": \"ok\", \"value\": []}",
        "input": "{\"config\": {}, \"operation\": \"parse\", \"text\": \"\\\"say \\\"\\\"hi\\\"\\\"\\\",end\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-doubled-quote"
        ]
      },
      {
        "id": "6370dc07688f337f",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-multiline\", \"status\": \"ok\", \"value\": [[\"line1\\nline2\", \"x\"]]}",
        "actual": "{\"id\": \"csv-v1-visible-multiline\", \"status\": \"ok\", \"value\": []}",
        "input": "{\"config\": {}, \"operation\": \"parse\", \"text\": \"\\\"line1\\nline2\\\",x\\n\"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-multiline"
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

## Attempt 1 — visible_failures_remain
```json
{
  "attempt": 1,
  "candidate_sha256": "7e11be3306ce9da76fd7a2aba55722bbf8225bcad428f6f3ece5ebdad28db9db",
  "accepted_checkpoint": true,
  "verification": "visible_failures_remain",
  "diagnostics": {
    "passed": 66,
    "total": 74,
    "groups_total": 4,
    "failures": [
      {
        "id": "489d27e30fff7d7c",
        "category": "runtime_exception",
        "expected": "{\"id\": \"csv-v1-visible-surrounding\", \"status\": \"ok\", \"value\": [[\"a\", \" b \"]]}",
        "actual": "{\"id\": \"csv-v1-visible-surrounding\", \"status\": \"exception\", \"type\": \"CSVParseError\"}",
        "input": "{\"config\": {\"ignore_surrounding_spaces\": true}, \"operation\": \"parse\", \"text\": \" a , \\\" b \\\" \"}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-surrounding"
        ]
      },
      {
        "id": "addb0480ada29493",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-printer-all-non-null\", \"status\": \"ok\", \"value\": \"N,\\\"\\\",\\\"x\\\"\\r\\n\"}",
        "actual": "{\"id\": \"csv-v1-visible-printer-all-non-null\", \"status\": \"ok\", \"value\": \"\\\"N\\\",\\\"\\\",\\\"x\\\"\\r\\n\"}",
        "input": "{\"config\": {\"null_string\": \"N\", \"quote_mode\": \"ALL_NON_NULL\"}, \"operation\": \"print\", \"records\": [[null, \"\", \"x\"]]}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-printer-all-non-null"
        ]
      },
      {
        "id": "993eb23e0f55e657",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-printer-none\", \"status\": \"ok\", \"value\": \"a\\\\,b,c\\\\nd\\r\\n\"}",
        "actual": "{\"id\": \"csv-v1-visible-printer-none\", \"status\": \"ok\", \"value\": \"a\\\\,b,c\\\\\\nd\\r\\n\"}",
        "input": "{\"config\": {\"escape\": \"\\\\\", \"quote_mode\": \"NONE\"}, \"operation\": \"print\", \"records\": [[\"a,b\", \"c\\nd\"]]}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-printer-none"
        ]
      },
      {
        "id": "d5dde6c82d1e39aa",
        "category": "behavioral_mismatch",
        "expected": "{\"id\": \"csv-v1-visible-printer-custom\", \"status\": \"ok\", \"value\": \"\\\"a;b\\\";\\\" c \\\"\\n\"}",
        "actual": "{\"id\": \"csv-v1-visible-printer-custom\", \"status\": \"ok\", \"value\": \"\\\"a;b\\\"; c \\n\"}",
        "input": "{\"config\": {\"delimiter\": \";\", \"record_separator\": \"\\n\"}, \"operation\": \"print\", \"records\": [[\"a;b\", \" c \"]]}",
        "occurrences": 2,
        "runtimes": [
          "cpython",
          "graal"
        ],
        "case_ids": [
          "csv-v1-visible-printer-custom"
        ]
      }
    ],
    "note": "Observations only, not inferred root causes. Full details remain in visible/summary.json."
  },
  "fix_status": "Code revision evaluated; causal explanation not established",
  "evidence": "attempts/01/visible/summary.json",
  "previously_failing_observations_now_passing": [
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-blank-kept"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-blank-kept"
    },
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-trailing-fields"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-trailing-fields"
    },
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-quoted-empty"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-quoted-empty"
    },
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-quoted-delimiter"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-quoted-delimiter"
    },
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-doubled-quote"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-doubled-quote"
    },
    {
      "runtime": "cpython",
      "case_id": "csv-v1-visible-multiline"
    },
    {
      "runtime": "graal",
      "case_id": "csv-v1-visible-multiline"
    }
  ],
  "attempted_revision_excerpt": "--- selected-checkpoint.py\n\n+++ attempt-candidate.py\n\n@@ -1,7 +1,58 @@\n\n-\"\"\"Intentionally incorrect, typed synthetic fixture; not a model translation.\"\"\"\n-def parse_csv(text, config):\n-    return []\n+\"\"\"Synthetic stdlib probe, NOT a claimed complete Commons CSV translation.\n+\n+Known differences are retained and reported by qualification, never hidden.\n+\"\"\"\n+import csv\n+import io\n+\n+class CSVParseError(Exception): pass\n+class IllegalArgumentException(Exception): pass\n \n \n-def print_csv(records, config):\n-    return ''\n+def settings(config):\n+    delimiter=config.get('delimiter',',');quote=config.get('quote','\"');escape=config.get('escape')\n+    for key,value in [('delimiter',delimiter),('quote',quote),('escape',escape)]:\n+        if value is None and key!='delimiter':continue\n+        if not isinstance(value,str) or len(value.encode('utf-16-le'))!=2 or value in ('\\r','\\n'):\n+            raise IllegalArgumentException()\n+    if delimiter==quote or delimiter==escape:raise IllegalArgumentException()\n+    for key in ('ignore_empty_lines','ignore_surrounding_spaces','trim'):\n+        if key in config and type(config[key]) is not bool:raise IllegalArgumentException()\n+    mode=config.get('quote_mode','MINIMAL')\n+    if mode not in ('ALL','ALL_NON_NULL','MINIMAL','NON_NUMERIC','NONE') or (mode=='NONE' and escape is None):\n+        raise IllegalArgumentException()\n+    return delimiter,quote,escape,mode\n+\n+\n+def parse_csv(text,config):\n+    delimiter,quote,escape,mode=settings(config)\n+    try:\n+        reader=csv.reader(io.StringIO(text,newline=''),delimiter=delimiter,quotechar=quote,\n+            escapechar=escape,quoting=csv.QUOTE_NONE if quote is None else csv.QUOTE_MINIMAL,\n+            skipinitialspace=config.get('ignore_surrounding_spaces',False),strict=True)\n+        result=[]\n+        for row in reader:\n+            if not row:\n+                if config.get('ignore_empty_lines',True):continue\n+                row=['']\n+            if config.get('trim',False):row=[v.strip() for v in row]\n+            if config.get('null_string') is not None:row=[None if v==config['null_string'] else v for v in row]\n+            result.append(row)\n+        return result\n+    except csv.Error as exc:raise CSVParseError(str(exc))\n+\n+\n+def print_csv(records,config):\n+    delimiter,quote,escape,mode=settings(config)\n+    quoting={'MINIMAL':csv.QUOTE_MINIMAL,'ALL':csv.QUOTE_ALL,'A \u2026 [truncated; see raw evidence]"
}
```
