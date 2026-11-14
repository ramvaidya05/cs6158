import json, math, traceback

def evaluate_candidate(source, cases, contract):
    scope = {"__name__": "candidate"}
    exec(compile(source, "candidate.py", "exec"), scope)
    if cases[0]["task"] == "commons_cli":
        validate_cases(cases, contract)
        validate_implementation(scope, contract)
        return [execute_scenario(scope, case, contract) for case in cases]
    rows = []
    for case in cases:
        row = {"id": case["id"]}
        try:
            value = scope["run"](case["a"], case["b"], case["operation"], case.get("parameter"))
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise TypeError("run must return a finite number, not bool")
            row.update(status="ok", value=value)
        except Exception as exc:
            row.update(status="exception", type=type(exc).__name__, message=str(exc), trace=traceback.format_exc(limit=8))
        rows.append(row)
    return rows

_result_json = json.dumps(evaluate_candidate(_source, json.loads(_cases_json), json.loads(_contract_json)), allow_nan=False)
_result_json
