"""Executed with python -I in an isolated temporary working directory.

This isolates imports and environment, not the operating system. Never use it as
a security sandbox. The parent owns timeouts and kills the process group.
"""
import contextlib
import json
import math
from pathlib import Path
import sys
import traceback


def main():
    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    cases = json.load(sys.stdin)
    if not cases:
        raise ValueError("Nonempty cases required")
    namespace = {"__name__": "candidate"}
    rows = []
    with contextlib.redirect_stdout(sys.stderr):
        exec(compile(source, "candidate.py", "exec"), namespace)
        fn = namespace["run"]
        for case in cases:
            row = {"id": case["id"]}
            try:
                value = fn(case["a"], case["b"], case["operation"], case.get("parameter"))
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise TypeError("run must return a finite number, not bool")
                row.update(status="ok", value=value)
            except Exception as exc:
                row.update(status="exception", type=type(exc).__name__, message=str(exc), trace=traceback.format_exc(limit=8))
            rows.append(row)
    print(json.dumps(rows, allow_nan=False))


if __name__ == "__main__":
    main()
