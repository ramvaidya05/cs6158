import json
import unicodedata
def run(operation, data):
    report = {}
    for name in ("category", "decimal", "digit"):
        method = getattr(unicodedata, name, None)
        entry = {"callable": callable(method)}
        if callable(method):
            try:
                entry["sample"] = method("1")
            except Exception as exc:
                entry["error"] = type(exc).__name__
        report[name] = entry
    return json.dumps(report, sort_keys=True)
