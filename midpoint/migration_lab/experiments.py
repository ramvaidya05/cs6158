"""Paired repeated trials, immutable selections, and failure-inclusive accuracy."""
import json
import math
from pathlib import Path
import shutil
import time
from .backends import InitialResponseBackend, AvailabilityGuard
from .controller import run_task, score_selected
from .environment import EnvironmentAgent
from .isolation import ContainerExecutor
from .protocol import FrozenSuite
from .storage import ROOT, new_run, save_json, sha256, protected_hashes

ARMS = ("one_shot", "code_repair", "environment_repair")


def wilson(successes, total):
    if not total:
        return None
    p, z = successes / total, 1.96
    scale = 1 + z*z / total
    center = (p + z*z / (2*total)) / scale
    radius = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / scale
    return [max(0, center-radius), min(1, center+radius)]


def usage_at(directory):
    counts = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "usage_unknown_calls": 0}
    for path in sorted((directory / "attempts").glob("*/*response.json")):
        response = json.loads(path.read_text())
        meta = response.get("metadata", {})
        if meta.get("reused_initial") or meta.get("provenance") != "live_model":
            continue
        counts["model_calls"] += 1
        usage = meta.get("usage")
        if usage:
            for key in ("input_tokens", "output_tokens"):
                counts[key] += usage.get(key, 0)
        else:
            counts["usage_unknown_calls"] += 1
    manifest = directory / "manifest.json"
    live = manifest.exists() and json.loads(manifest.read_text())["backend"]["provenance"] == "live_model"
    for path in sorted((directory / "attempts").glob("*/backend-error.json")):
        error = json.loads(path.read_text())
        if not live or error.get("kind") in ("budget", "provider_circuit_open"):
            continue
        counts["model_calls"] += 1
        raw = error.get("raw_response")
        usage = raw.get("usage") if isinstance(raw, dict) else None
        if usage:
            for key in ("input_tokens", "output_tokens"):
                counts[key] += usage.get(key, 0)
        else:
            counts["usage_unknown_calls"] += 1
    return counts


def summarize_arms(records, runtimes):
    arms = {}
    for arm in ARMS:
        group = [r for r in records if r["arm"] == arm]
        passed = sum(r["validated"] for r in group)
        completed = sum(r["status"] == "completed" for r in group)
        summary = {"tasks_passing": passed, "admitted_task_trials": len(group),
                   "completed_task_trials": completed,
                   "task_pass_rate": passed / len(group) if group else None,
                   "pass_rate_among_completed": passed / completed if completed else None,
                   "descriptive_wilson_95": wilson(passed, len(group)), "runtimes": {}}
        for mode in runtimes:
            summary["runtimes"][mode] = {}
            for split in ("visible", "holdout"):
                rows = [r["runtimes"][mode][split] for r in group]
                total = sum(r["total"] for r in rows)
                count = sum(r["passed"] for r in rows)
                summary["runtimes"][mode][split] = {"passed": count, "total": total,
                    "rate": count / total if total else None,
                    "unvalidated": sum(r["unvalidated"] for r in rows)}
        arms[arm] = summary
    return arms


def repair_opportunities(records, pairs):
    initials = [r for r in records if r["arm"] == "one_shot"]
    observed = [r for r in initials if r["status"] == "completed"]
    eligible = [r for r in observed if r["visible_all_pass"] is False]
    return {"admitted_initials": len(initials), "completed_initials": len(observed),
            "initials_with_visible_failures": len(eligible),
            "initials_passing_visible": sum(r["visible_all_pass"] is True for r in observed),
            "arms": {arm: {
                "eligible_pairs_completed": sum(p["comparable"] and p["repair_eligible"] for p in pairs if p["arm"] == arm),
                "eligible_pairs_fully_recovered": sum(p["comparable"] and p["repair_eligible"] and p["final_validated"] for p in pairs if p["arm"] == arm),
                "pairs_with_holdout_regression": sum(p["comparable"] and any(d < 0 for d in p["holdout_delta_percentage_points"].values()) for p in pairs if p["arm"] == arm),
            } for arm in ARMS[1:]},
            "interpretation": "Repair eligibility uses visible failures only. Zero eligible initials gives no evidence of code-repair effectiveness."}


def aggregate(directory, *, persist=True):
    plan = json.loads((directory / "experiment.json").read_text())
    records = []
    for item in plan["planned_runs"]:
        folder = directory / item["path"]
        path = folder / "result.json"
        state = json.loads(path.read_text()) if path.exists() else {"status": "not_run"}
        record = {**item, "status": state["status"], "validated": bool(state.get("validated", False)) and state["status"] == "completed",
                  "stop_reason": state.get("stop_reason"), "error": state.get("error"),
                  "not_run_reason": state.get("not_run_reason"),
                  "visible_all_pass": state.get("selected_visible", {}).get("all_pass"),
                  "attempts": len(state.get("attempts", [])),
                  "code_repairs": max(0, len(state.get("attempts", [])) - 1),
                  "environment_repairs": len(state.get("environment_actions", [])),
                  "elapsed_seconds": state.get("elapsed_seconds", 0), "usage": usage_at(folder), "runtimes": {}}
        for mode in plan["runtimes"]:
            visible_n = plan["suite"]["counts"][item["task"]]["visible"]
            held_n = plan["suite"]["counts"][item["task"]]["holdout"]
            scores = {}
            for split, count in (("visible", visible_n), ("holdout", held_n)):
                observed = state.get("selected_" + split, {}).get("runtimes", {}).get(mode)
                # Integrity-invalid/error runs retain evidence but earn no accuracy credit.
                valid = state["status"] == "completed" and observed is not None
                passed = observed["passed"] if valid else 0
                scores[split] = {"passed": passed, "total": count, "rate": passed / count,
                                 "unvalidated": 0 if valid and observed["status"] == "completed" else count}
            record["runtimes"][mode] = scores
        records.append(record)
    arms = summarize_arms(records, plan["runtimes"])
    pairs = []
    for initial in (r for r in records if r["arm"] == "one_shot"):
        for arm in ("code_repair", "environment_repair"):
            selected = next(r for r in records if r["trial"] == initial["trial"] and r["task"] == initial["task"] and r["arm"] == arm)
            pairs.append({"trial": initial["trial"], "task": initial["task"], "arm": arm,
                          "comparable": initial["status"] == selected["status"] == "completed",
                          "repair_eligible": initial["status"] == "completed" and initial["visible_all_pass"] is False,
                          "final_validated": selected["validated"],
                          "task_success_delta": int(selected["validated"]) - int(initial["validated"]),
                          "holdout_delta_percentage_points": {mode: 100 * (selected["runtimes"][mode]["holdout"]["rate"] - initial["runtimes"][mode]["holdout"]["rate"]) for mode in plan["runtimes"]}})
    result = {"provenance": plan["backend"]["provenance"], "study": plan["study"],
              "measurement_status": "evaluated" if any(r["status"] == "completed" for r in records) else "no_completed_evaluations",
              "interpretation": "Test-supported behavioral parity on this pilot; repeated trials/cases are not independent repositories.",
              "arms": arms, "paired_changes": pairs, "runs": records,
              "repair_opportunities": repair_opportunities(records, pairs),
              "by_task": {task: {"arms": summarize_arms([r for r in records if r["task"] == task], plan["runtimes"]),
                  "repair_opportunities": repair_opportunities([r for r in records if r["task"] == task],
                                                               [p for p in pairs if p["task"] == task])}
                  for task in sorted({r["task"] for r in records})},
              "usage": {key: sum(r["usage"][key] for r in records) for key in ("model_calls", "input_tokens", "output_tokens", "usage_unknown_calls")}}
    if persist:
        save_json(directory / "summary.json", result)
    return result


def archive_run(directory):
    destination = ROOT / "evidence" / directory.name
    shutil.copytree(directory, destination)
    save_json(destination / "checksums.json", {str(p.relative_to(destination)): sha256(p)
              for p in sorted(destination.rglob("*")) if p.is_file()})
    return destination


def run_experiment(backend, suite, *, tasks=("levenshtein",), trials=3, max_repairs=5,
                   timeout=60, max_seconds=900, max_output_tokens=8192,
                   output_token_budget=49152, fault="none", directory=None):
    if trials < 1 or trials > 100 or not 0 <= max_repairs <= 5:
        raise ValueError("Trials must be 1..100 and repairs 0..5")
    if not tasks or len(set(tasks)) != len(tasks) or any(t not in suite.identity()["counts"] for t in tasks):
        raise ValueError("Unknown or repeated task")
    if backend.identity.get("provenance") == "live_model":
        backend = AvailabilityGuard(backend)
    directory = directory or new_run("experiment")
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(suite.path, directory / "evaluation-suite.json")
    suite = FrozenSuite(directory / "evaluation-suite.json")
    planned = [{"trial": trial, "task": task, "arm": arm,
                "path": f"trial-{trial:03}/{task}/{arm}"}
               for trial in range(trials) for task in tasks for arm in ARMS]
    plan = {"schema": 1, "backend": backend.identity, "suite": suite.identity(),
            "planned_runs": planned, "runtimes": ["cpython", "graal"], "max_repairs": max_repairs,
            "study": "natural_translation" if fault == "none" else "controlled_environment_stress",
            "fault": fault, "protected_hashes": protected_hashes(),
            "settings": {"timeout": timeout, "max_seconds": max_seconds,
                         "max_output_tokens": max_output_tokens, "output_token_budget": output_token_budget},
            "pairing": "One initial response per task/trial (fresh only for live_model), reused verbatim in both repair arms; "
                       "every selection freezes before any holdout scoring. Stress fault affects both repair arms; one-shot is healthy."}
    save_json(directory / "experiment.json", plan)
    for item in planned:
        save_json(directory / item["path"] / "result.json", {"status": "not_run", "task": item["task"]})
    if getattr(backend, "budget", None):
        backend.budget.path = directory / "spend.json"
        backend.budget.record()
    environments = {}
    try:
        for trial in range(trials):
            for task in tasks:
                base = directory / f"trial-{trial:03}" / task
                paired = None
                for arm in ARMS:
                    folder = base / arm
                    if getattr(backend, "stop", None):
                        save_json(directory / "provider-stop.json", backend.stop)
                        save_json(folder / "result.json", {"status": "not_run", "task": task,
                                  "not_run_reason": "provider_circuit_open", "stop_reason": backend.stop["reason"]})
                        continue
                    started = time.monotonic()
                    try:
                        env = EnvironmentAgent(timeout, ContainerExecutor(fault="none" if arm == "one_shot" else fault))
                        environments[str(folder)] = env
                        if arm != "one_shot" and paired is None:
                            raise RuntimeError("Initial generation failed; paired arm remains unvalidated")
                        print(f"Trial {trial + 1}/{trials}: {task}, {arm}", flush=True)
                        run_task(task, backend if arm == "one_shot" else paired,
                                 max_repairs=0 if arm == "one_shot" else max_repairs,
                                 timeout=timeout, max_seconds=max_seconds,
                                 max_output_tokens=max_output_tokens, output_token_budget=output_token_budget,
                                 directory=folder, environment=env, suite=suite,
                                 environment_repairs=arm == "environment_repair", defer_holdout=True)
                        if arm == "one_shot":
                            paired = InitialResponseBackend(backend,
                                json.loads((folder / "attempts/00/response.json").read_text()),
                                (folder / "attempts/00/prompt.txt").read_text())
                    except Exception as exc:
                        state = json.loads((folder / "result.json").read_text())
                        state.update(status="error", validated=False,
                                     error={"type": type(exc).__name__, "message": str(exc)},
                                     elapsed_seconds=time.monotonic() - started)
                        save_json(folder / "result.json", state)
                    aggregate(directory)
        # No M-Agent calls after this point. Freeze across every trial and arm.
        save_json(directory / "selections-frozen.json", {item["path"]: sha256(directory / item["path"] / "selection.json")
                  for item in planned if (directory / item["path"] / "selection.json").exists()})
        for item in planned:
            folder = directory / item["path"]
            if str(folder) in environments:
                score_selected(folder, environments[str(folder)], suite)
    finally:
        if getattr(backend, "stop", None):
            save_json(directory / "provider-stop.json", backend.stop)
        aggregate(directory)
    return directory, aggregate(directory)
