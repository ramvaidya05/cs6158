"""T-Agent: fixed, execution-based comparison, independent of model assertions."""
import math
from .storage import save_json


def equivalent(expected, actual):
    if expected["status"] != actual.get("status"):
        return False
    if expected["status"] == "exception":
        # Explicit cross-language exception contract; messages are recorded, not scored.
        return expected["type"] == "NullPointerException" and actual.get("type") == "ValueError"
    value = actual.get("value")
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return False
    try:
        return math.isfinite(value) and math.isclose(expected["value"], value, rel_tol=1e-9, abs_tol=1e-9)
    except OverflowError:
        return False


class TestsuiteAgent:
    def __init__(self, environment):
        self.environment = environment

    def reference(self, cases, directory):
        result = self.environment.run("reference", cases, directory)
        if result["status"] != "completed":
            raise RuntimeError(f"Java reference failed: see {directory}")
        return result["rows"]

    def evaluate(self, candidate, cases, reference, modes, directory):
        if not cases or not modes or len(reference) != len(cases):
            raise ValueError("Nonempty matched cases/reference and runtimes required")
        results = {}
        for mode in modes:
            observed = self.environment.run(mode, cases, directory / mode, candidate)
            failures = []
            passed = 0
            passed_ids = []
            if observed["status"] == "completed":
                for case, expected, actual in zip(cases, reference, observed["rows"], strict=True):
                    if equivalent(expected, actual):
                        passed += 1
                        passed_ids.append(case["id"])
                    else:
                        failures.append({"case": case, "expected": expected, "actual": actual})
            else:
                failures = [{"kind": observed["status"], "detail": observed.get("detail", ""),
                             "stderr": observed.get("process", {}).get("stderr", "")[-6000:]}]
            results[mode] = {"passed": passed, "total": len(cases), "status": observed["status"],
                             "passed_ids": passed_ids, "failures": failures}
        summary = {"runtimes": results, "passed": sum(x["passed"] for x in results.values()),
                   "total": len(cases) * len(modes),
                   "all_pass": all(x["passed"] == len(cases) for x in results.values())}
        save_json(directory / "summary.json", summary)
        return summary
