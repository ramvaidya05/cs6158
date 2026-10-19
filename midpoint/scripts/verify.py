"""Run the midpoint acceptance suite and optionally archive its complete evidence."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.backends import ReplayBackend
from migration_lab.benchmark import TASKS, verify_vendor
from migration_lab.build import verify_build
from migration_lab.controller import run_task
from migration_lab.process import execute
from migration_lab.storage import new_run, save_json, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", action="store_true", help="Copy complete artifacts to evidence/ for handoff")
    args = parser.parse_args()
    build = verify_build()
    verify_vendor()
    directory = new_run("verification")
    save_json(directory / "java-build.json", build)
    print(f"Verification artifacts: {directory}", flush=True)
    unit = execute([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, timeout=60)
    save_json(directory / "unit-tests.json", unit)
    if unit["exit_code"] != 0:
        print(unit["stderr"], file=sys.stderr)
        return 1
    java = []
    reports = sorted((ROOT / "java/target/surefire-reports").glob("TEST-*.xml"))
    if not reports:
        raise RuntimeError("Missing upstream JUnit reports; rerun bootstrap")
    for path in reports:
        suite = ET.parse(path).getroot()
        result = {key: suite.attrib[key] for key in ("name", "tests", "errors", "failures", "skipped")}
        java.append(result)
        destination = directory / "upstream-junit" / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    if any(int(r["failures"]) or int(r["errors"]) or int(r["skipped"]) for r in java):
        raise RuntimeError("Upstream JUnit suite is not fully passing")
    save_json(directory / "java-tests.json", java)
    summaries = []
    backend = ReplayBackend(ROOT / "fixtures/replay.json")
    for task in TASKS:
        print(f"Verifying {task}: Java, CPython, GraalPy; synthetic replay only", flush=True)
        _, result = run_task(task, backend, directory=directory / task, timeout=90)
        row = {"task": task, "attempts": len(result["attempts"]), "validated": result["validated"],
               "elapsed_seconds": result["elapsed_seconds"]}
        for key in ("baseline_visible", "selected_visible", "baseline_holdout", "selected_holdout"):
            row[key] = {name: result[key][name] for name in ("passed", "total", "all_pass")}
        summaries.append(row)
        if not result["validated"] or result["baseline_visible"]["all_pass"]:
            raise RuntimeError("Acceptance failed: must reject broken fixture and validate correct fixture")
    selected_checks = sum(row[key]["total"] for row in summaries
                          for key in ("selected_visible", "selected_holdout"))
    summary = {"provenance": "synthetic_fixture", "interpretation": "Harness acceptance, not LLM performance",
               "unique_task_cases": selected_checks // 2, "selected_runtime_checks": selected_checks,
               "upstream_junit_test_methods": sum(int(x["tests"]) for x in java),
               "unit_tests_passed": unit["exit_code"] == 0, "tasks": summaries}
    save_json(directory / "summary.json", summary)
    if args.archive:
        destination = ROOT / "evidence" / directory.name
        shutil.copytree(directory, destination)
        checksums = {str(p.relative_to(destination)): sha256(p) for p in sorted(destination.rglob("*")) if p.is_file()}
        save_json(destination / "checksums.json", checksums)
        print(f"Archived complete evidence: {destination}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
