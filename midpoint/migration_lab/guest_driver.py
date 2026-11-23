import json, math, traceback

def evaluate_candidate(source, cases, contract):
    scope = {"__name__": "candidate"}
    exec(compile(source, "candidate.py", "exec"), scope)
    if cases[0]["task"] == "commons_cli":
        validate_cases(cases, contract)
        validate_implementation(scope, contract)
        return [execute_scenario(scope, case, contract) for case in cases]
    if cases[0]["task"] == "commons_csv":
        for name in ("parse_csv", "print_csv"):
            if not callable(scope.get(name)):
                raise TypeError("Candidate must define " + name)
        rows = []
        for case in cases:
            row = {"id": case["id"]}
            try:
                config = json.loads(json.dumps(case.get("config", {})))
                if case["operation"] == "parse":
                    value = scope["parse_csv"](case["text"], config)
                    if not isinstance(value, list) or any(not isinstance(record, list) or
                            any(v is not None and not isinstance(v, str) for v in record) for record in value):
                        raise TypeError("Parser must return nested string/null lists")
                else:
                    value = scope["print_csv"](json.loads(json.dumps(case["records"])), config)
                    if not isinstance(value, str):
                        raise TypeError("Printer must return a string")
                row.update(status="ok", value=value)
            except Exception as exc:
                row.update(status="exception", type=type(exc).__name__)
            rows.append(row)
        return rows
    if cases[0]["task"] == "commons_validator_luhn":
        rows = []
        for case in cases:
            row = {"id": case["id"]}
            try:
                value = scope["run"](case["operation"], case["data"])
                if case["operation"] == "isValid":
                    if type(value) is not bool:
                        raise TypeError("isValid must return bool")
                elif not isinstance(value, str):
                    raise TypeError("calculate must return string")
                row.update(status="ok", value=value)
            except ValueError:
                row.update(status="exception", type="CheckDigitException")
            except Exception as exc:
                row.update(status="exception", type=type(exc).__name__,
                           diagnostic={"message": str(exc)[:2000],
                                       "traceback": traceback.format_exc(limit=8)[-6000:]})
            rows.append(row)
        return rows
    if cases[0]["task"] == "commons_codec_hex":
        if not callable(scope.get("run")):
            raise TypeError("Candidate must define run(operation, data, lower)")
        rows = []
        for case in cases:
            row = {"id": case["id"]}
            try:
                value = scope["run"](case["operation"], case["data"], case.get("lower", True))
                if case["operation"] == "encode":
                    if not isinstance(value, str):
                        raise TypeError("Encode must return a string")
                elif not isinstance(value, list) or any(type(v) is not int or not 0 <= v <= 255 for v in value):
                    raise TypeError("Decode must return unsigned byte values")
                row.update(status="ok", value=value)
            except ValueError:
                row.update(status="exception", type="DecoderException")
            except Exception as exc:
                row.update(status="exception", type=type(exc).__name__,
                           diagnostic={"message": str(exc)[:2000],
                                       "traceback": traceback.format_exc(limit=8)[-6000:]})
            rows.append(row)
        return rows
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
