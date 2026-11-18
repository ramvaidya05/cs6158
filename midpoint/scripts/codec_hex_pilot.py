"""One bounded live Commons Codec Hex translation with frozen Java-oracle cases."""
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

TASK = "commons_codec_hex"
MODEL = "gemini-3.5-flash-lite"
MAX_OUTPUT = 2048
MAX_TOTAL_TOKEN_RESERVATION = 18000
MAX_CALLS = 2
MAX_SPEND_USD = 0.03
SOURCE = ROOT / "vendor/commons-codec/Hex.java"
SOURCE_LINES = ((57, 62), (73, 76), (91, 108), (121, 123), (133, 148),
                (162, 165), (208, 214), (276, 290), (330, 331), (365, 370))


def verify_source():
    manifest = json.loads((SOURCE.parent / "SOURCE.json").read_text())
    for name, digest in manifest["files"].items():
        if sha256(SOURCE.parent / name) != digest:
            raise RuntimeError("Pinned Commons Codec source changed: " + name)
    return manifest


def cases():
    visible = []
    holdout = []
    def add(dest, operation, data, lower=True):
        dest.append({"id": f"codec-{('visible' if dest is visible else 'holdout')}-{len(dest):03}",
                     "task": TASK, "operation": operation, "data": data, "lower": lower})
    for data, lower in [([], True), ([], False), ([0], True), ([255], False),
                        ([0, 15, 16, 127, 128, 255], True), ([1, 171, 205], False)]:
        add(visible, "encode", data, lower)
    for value in ("", "00", "ff", "Ff", "0F10ff", "a", "abz1", "zz", "ff ", "123"):
        add(visible, "decode", value)
    rng = random.Random(6158)
    for n in range(32):
        data = [rng.randrange(256) for _ in range(rng.randrange(0, 25))]
        add(holdout, "encode", data, n % 2 == 0)
        encoded = "".join(f"{v:02x}" for v in data)
        add(holdout, "decode", encoded.upper() if n % 3 == 0 else encoded)
    for value in ("０Ａ", "Ａｆ", "١f", "0f0", "0g", "é0", "\U0001d7d0f", "f\u0000", "\u0660\u0661"):
        add(holdout, "decode", value)
    return {"visible": visible, "holdout": holdout}


def prompt(previous=None, failures=None):
    lines = SOURCE.read_text().splitlines()
    excerpt = "\n".join(f"{i}: {lines[i - 1]}" for start, end in SOURCE_LINES for i in range(start, end + 1))
    instruction = (
        "Translate the pinned Apache Commons Codec 1.22.1 Hex methods below into a standalone Python module. "
        "Define run(operation, data, lower=True). For encode, data is a list of unsigned bytes and return the "
        "hex string (lowercase if lower is true). For decode, data is a string and return a list of unsigned "
        "bytes. Raise ValueError on odd length or an illegal digit. Preserve Java Character.digit(ch, 16) "
        "behavior, including Unicode digits. Do not use network, files, or subprocesses. Return the required "
        "JSON object with code and explanation.\n\nPinned Java excerpt (line numbers from Hex.java):\n" + excerpt)
    if previous is not None:
        instruction += ("\n\nPrevious Python candidate:\n" + previous +
                        "\n\nVisible failures only; repair general behavior:\n" +
                        json.dumps(failures[:8], ensure_ascii=True))
    return instruction


def score(environment, candidate, rows, reference, split, directory):
    result = {}
    for mode in ("cpython", "graal"):
        observed = environment.run(mode, rows, directory / split / mode, candidate)
        mismatches = []
        if observed["status"] == "completed":
            for case, expected, actual in zip(rows, reference, observed["rows"], strict=True):
                if expected != actual:
                    mismatches.append({"case": case, "expected": expected, "actual": actual})
        else:
            mismatches = [{"kind": observed["status"], "detail": observed.get("detail", "")}]
        failed_ids = {f["case"]["id"] for f in mismatches if "case" in f}
        result[mode] = {"status": observed["status"], "passed": len(rows) - len(mismatches) if observed["status"] == "completed" else 0,
                        "total": len(rows), "passed_ids": [c["id"] for c in rows if c["id"] not in failed_ids]
                        if observed["status"] == "completed" else [], "failures": mismatches}
    save_json(directory / split / "score.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="Freeze and verify the Java oracle without model calls")
    args = parser.parse_args()
    source = verify_source()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = ROOT / ".cache" / f"{stamp}-codec-hex-pilot"
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
    budget = SpendBudget(MAX_SPEND_USD, 0.30, 2.50, directory / "spend.json")
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
