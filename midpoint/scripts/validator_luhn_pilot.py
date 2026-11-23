"""One bounded live Commons Validator Luhn translation with frozen Java-oracle cases."""
import argparse
import json
import os
from pathlib import Path
import random
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.backends import BackendError, GeminiBackend
from migration_lab.budget import SpendBudget
from migration_lab.credentials import load_key
from migration_lab.environment import EnvironmentAgent
from migration_lab.evaluation import TestsuiteAgent
from migration_lab.experiments import archive_run
from migration_lab.isolation import ContainerExecutor
from migration_lab.storage import save_json, sha256

TASK = "commons_validator_luhn"
MODEL = "gemini-3.5-flash"
MAX_OUTPUT = 4096
MAX_TOTAL_TOKEN_RESERVATION = 40000
MAX_CALLS = 2
MAX_SPEND_USD = 0.15
SOURCE = ROOT / "vendor/commons-validator/LuhnCheckDigit.java"


def verify_source():
    manifest = json.loads((SOURCE.parent / "SOURCE.json").read_text())
    for name, digest in manifest["files"].items():
        if sha256(SOURCE.parent / name) != digest:
            raise RuntimeError("Pinned Commons Validator source changed: " + name)
    return manifest


def cases():
    visible = []
    holdout = []
    def add(dest, value):
        for operation in ("calculate", "isValid"):
            dest.append({"id": f"validator-{'visible' if dest is visible else 'holdout'}-{len(dest)}",
                         "task": TASK, "operation": operation, "data": value})
    for value in (None, "", "0", "0000", "7992739871", "79927398713", "79927398714",
                  "1", "18", "12a", " 12", "１２", "١٢", "²3", "𝟙2"):
        add(visible, value)
    rng = random.Random(6158)
    for n in range(50):
        add(holdout, ''.join(str(rng.randrange(10)) for _ in range(rng.randrange(1, 65))))
    for value in ("9", "00", "000000000", "\t", "12\n", "1\x002", "६७", "４９",
                  "٤٥٦", "Ⅳ2", "𝟠9", "-12", "12.3", "\u00a0", "9" * 1000):
        add(holdout, value)
    return {"visible": visible, "holdout": holdout}


def prompt(previous=None, failures=None):
    import re
    excerpt = "\n".join(re.sub(r"/\*.*?\*/", "", (SOURCE.parent / name).read_text(), flags=re.S)
                        for name in ("LuhnCheckDigit.java", "ModulusCheckDigit.java"))
    instruction = (
        "Translate Apache Commons Validator 1.9.0 LuhnCheckDigit calculate and isValid, including inherited behavior. "
        "Define run(operation, data), operation calculate or isValid; data is str or None. "
        "calculate returns a check-digit string or raises ValueError for CheckDigitException; isValid returns bool. "
        "GenericValidator.isBlankOrNull means null or Java trim().length()==0. Preserve Java char UTF-16 semantics. "
        "Target CPython 3.12 and GraalPy 25.0.0; only portable standard library, no files/network/subprocesses. "
        "Return the required JSON object with code and explanation.\nPinned Java source:\n" + excerpt)
    if previous is not None:
        instruction += "\nPrevious candidate:\n" + previous + "\nVisible failures only:\n" + json.dumps(failures[:8], ensure_ascii=True)
    return instruction


def score(environment, candidate, rows, reference, split, directory):
    result = {}
    for mode in ("cpython", "graal"):
        observed = environment.run(mode, rows, directory / split / mode, candidate)
        mismatches = []
        if observed["status"] == "completed":
            for case, expected, actual in zip(rows, reference, observed["rows"], strict=True):
                if not equivalent_observation(expected, actual):
                    mismatches.append({"case": case, "expected": expected, "actual": actual})
        else:
            mismatches = [{"kind": observed["status"], "detail": observed.get("detail", "")}]
        failed_ids = {f["case"]["id"] for f in mismatches if "case" in f}
        result[mode] = {"status": observed["status"], "passed": len(rows) - len(mismatches) if observed["status"] == "completed" else 0,
                        "total": len(rows), "passed_ids": [c["id"] for c in rows if c["id"] not in failed_ids]
                        if observed["status"] == "completed" else [], "failures": mismatches}
    save_json(directory / split / "score.json", result)
    return result


def equivalent_observation(expected, actual):
    """Diagnostics inform repair but never change the observable contract."""
    return expected == {key: value for key, value in actual.items() if key != "diagnostic"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="Freeze and verify the Java oracle without model calls")
    args = parser.parse_args()
    source = verify_source()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = ROOT / ".cache" / f"{stamp}-validator-luhn-pilot"
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    plan = {"task": TASK, "source": source, "source_sha256": sha256(SOURCE), "model": MODEL,
            "thinking": "low", "max_calls": MAX_CALLS, "max_output_tokens_per_call": MAX_OUTPUT,
            "total_token_reservation_cap": MAX_TOTAL_TOKEN_RESERVATION, "usd_reservation_cap": MAX_SPEND_USD,
            "case_seed": 6158, "runtimes": ["cpython", "graal"], "max_repairs": 1}
    save_json(directory / "plan.json", plan)
    suite = cases()
    trusted = EnvironmentAgent()
    tester = TestsuiteAgent(trusted)
    frozen = {"cases": suite, "reference": {}}
    for split in ("visible", "holdout"):
        frozen["reference"][split] = tester.reference(suite[split], directory / "oracle" / split)
        repeated = tester.reference(suite[split], directory / "oracle" / (split + "-repeat"))
        if frozen["reference"][split] != repeated:
            raise RuntimeError("Java oracle was not deterministic")
    save_json(directory / "frozen-suite.json", frozen)
    if args.prepare_only:
        print("Prepared:", directory, "visible", len(suite["visible"]), "holdout", len(suite["holdout"]))
        return 0
    executor = ContainerExecutor()
    environment = EnvironmentAgent(timeout=45, executor=executor)
    load_key(provider="gemini")
    budget = SpendBudget(MAX_SPEND_USD, 1.50, 9.00, directory / "spend.json")
    backend = GeminiBackend(MODEL, "low", budget)
    record = {"status": "started", "calls": [], "candidates": [], "suite_sha256": sha256(directory / "frozen-suite.json")}
    reservation = 0
    previous = failures = None
    visible_history = []
    try:
        for attempt in range(MAX_CALLS):
            question = prompt(previous, failures)
            allowance = len(question.encode("utf-8")) + 1024 + MAX_OUTPUT
            if reservation + allowance > MAX_TOTAL_TOKEN_RESERVATION:
                record["status"] = "token_cap"
                break
            reservation += allowance
            call = {"attempt": attempt, "prompt_utf8_bytes": len(question.encode("utf-8")),
                    "reserved_tokens": allowance, "cumulative_reserved_tokens": reservation}
            save_json(directory / f"prompt-{attempt}.json", {"prompt": question})
            try:
                response = backend.generate(TASK, attempt, question, timeout=60, max_output_tokens=MAX_OUTPUT)
                call["metadata"] = response["metadata"]
                save_json(directory / f"response-{attempt}.json", {k: response[k] for k in ("code", "explanation", "metadata")})
                candidate = directory / f"candidate-{attempt}.py"
                candidate.write_text(response["code"])
                call["candidate_sha256"] = sha256(candidate)
                score_visible = score(environment, candidate, suite["visible"], frozen["reference"]["visible"],
                                      "visible", directory / f"attempt-{attempt}")
                call["visible"] = {mode: {"passed": item["passed"], "total": item["total"], "status": item["status"]}
                                   for mode, item in score_visible.items()}
                record["candidates"].append(str(candidate.name))
                visible_history.append(score_visible)
                previous = response["code"]
                failures = next((item["failures"] for item in score_visible.values() if item["failures"]), [])
                record["calls"].append(call)
                if not failures:
                    break
            except BackendError as exc:
                call["error"] = {"kind": exc.kind, "message": str(exc), "details": exc.details}
                record["calls"].append(call)
                record["status"] = "model_error"
                break
        if record["candidates"]:
            baseline = directory / record["candidates"][0]
            record["holdout_baseline"] = score(environment, baseline, suite["holdout"],
                                                frozen["reference"]["holdout"], "holdout", directory / "attempt-0")
            selected = 0
            if len(record["candidates"]) > 1:
                baseline_pass = {m: set(visible_history[0][m]["passed_ids"]) for m in ("cpython", "graal")}
                repaired_pass = {m: set(visible_history[-1][m]["passed_ids"]) for m in ("cpython", "graal")}
                if (all(baseline_pass[m] <= repaired_pass[m] for m in baseline_pass)
                        and any(baseline_pass[m] < repaired_pass[m] for m in baseline_pass)):
                    selected = len(record["candidates"]) - 1
            record["selected_attempt"] = selected
            if selected == 0:
                record["holdout_final"] = record["holdout_baseline"]
            else:
                final = directory / record["candidates"][selected]
                record["holdout_final"] = score(environment, final, suite["holdout"],
                                                 frozen["reference"]["holdout"], "holdout",
                                                 directory / f"attempt-{selected}")
            record["status"] = "evaluated"
        record["usage"] = budget.record()
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save_json(directory / "summary.json", record)
        archived = archive_run(directory)
        print("Archive:", archived)
        print("Status:", record["status"])
        print("Model calls:", len(record["calls"]))
        print("Provider usage:", [(c.get("metadata") or {}).get("usage") for c in record["calls"]])
        print("Baseline holdout:", {m: (v["passed"], v["total"]) for m, v in record.get("holdout_baseline", {}).items()})
        print("Final holdout:", {m: (v["passed"], v["total"]) for m, v in record.get("holdout_final", {}).items()})
        return 0 if record["status"] == "evaluated" else 1
    finally:
        os.environ.pop("GEMINI_API_KEY", None)


if __name__ == "__main__":
    raise SystemExit(main())
