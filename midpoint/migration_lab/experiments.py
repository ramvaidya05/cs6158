"""Paired repeated trials, immutable selections, and failure-inclusive accuracy."""
import json
import math
from pathlib import Path
import shutil
import time
from .backends import InitialResponseBackend
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
        if not live or error.get("kind") == "budget":
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


def aggregate(directory, output_path=None):
    plan = json.loads((directory / "experiment.json").read_text())
    records = []
    for item in plan["planned_runs"]:
        folder = directory / item["path"]
        path = folder / "result.json"
        state = json.loads(path.read_text()) if path.exists() else {"status": "not_run"}
        record = {**item, "status": state["status"], "validated": bool(state.get("validated", False)) and state["status"] == "completed",
                  "stop_reason": state.get("stop_reason"), "error": state.get("error"),
                  "attempts": len(state.get("attempts", [])),
                  "repair_attempts": max(0, len(state.get("attempts", [])) - 1),
                  "code_repairs": sum(a.get("status") == "evaluated" for a in state.get("attempts", [])[1:]),
                  "repair_budget_blocked": state.get("backend_failure", {}).get("kind") == "budget",
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
    arms = {}
    for arm in plan.get("arms", ARMS):
        group = [r for r in records if r["arm"] == arm]
        passed = sum(r["validated"] for r in group)
        arms[arm] = {"tasks_passing": passed, "admitted_task_trials": len(group),
                     "task_pass_rate": passed / len(group) if group else None,
                     "descriptive_wilson_95": wilson(passed, len(group)),
                     "repair_budget_blocked_trials": sum(r["repair_budget_blocked"] for r in group),
                     "runtimes": {}}
        for mode in plan["runtimes"]:
            arms[arm]["runtimes"][mode] = {}
            for split in ("visible", "holdout"):
                rows = [r["runtimes"][mode][split] for r in group]
                total = sum(r["total"] for r in rows)
                count = sum(r["passed"] for r in rows)
                arms[arm]["runtimes"][mode][split] = {"passed": count, "total": total,
                    "rate": count / total if total else None,
                    "unvalidated": sum(r["unvalidated"] for r in rows)}
    pairs = []
    for initial in (r for r in records if r["arm"] == "one_shot"):
        for arm in (a for a in plan.get("arms", ARMS) if a != "one_shot"):
            selected = next(r for r in records if r["trial"] == initial["trial"] and r["task"] == initial["task"] and r["arm"] == arm)
            pairs.append({"trial": initial["trial"], "task": initial["task"], "arm": arm,
                          "task_success_delta": int(selected["validated"]) - int(initial["validated"]),
                          "repair_budget_blocked": selected["repair_budget_blocked"],
                          "holdout_delta_percentage_points": {mode: 100 * (selected["runtimes"][mode]["holdout"]["rate"] - initial["runtimes"][mode]["holdout"]["rate"]) for mode in plan["runtimes"]}})
    result = {"provenance": plan["backend"]["provenance"], "study": plan["study"],
              "measurement_status": "evaluated" if any(r["status"] == "completed" for r in records) else "no_completed_evaluations",
              "interpretation": "Test-supported behavioral parity on this pilot; repeated trials/cases are not independent repositories.",
              "arms": arms, "paired_changes": pairs, "runs": records,
              "usage": {key: sum(r["usage"][key] for r in records) for key in ("model_calls", "input_tokens", "output_tokens", "usage_unknown_calls")}}
    save_json(output_path or directory / "summary.json", result)
    return result


def archive_run(directory):
    destination = ROOT / "evidence" / directory.name
    shutil.copytree(directory, destination)
    save_json(destination / "checksums.json", {str(p.relative_to(destination)): sha256(p)
              for p in sorted(destination.rglob("*")) if p.is_file()})
    return destination


def run_experiment(backend, suite, *, tasks=("levenshtein",), trials=3, max_repairs=5,
                   timeout=60, model_timeout=120, max_seconds=900, max_output_tokens=8192,
                   output_token_budget=49152, fault="none", directory=None, feedback_ablation=False, budget_policy="partitioned", retry_memory=False, memory_ablation=False):
    if budget_policy not in ("partitioned", "shared"):
        raise ValueError("Unknown budget policy")
    if feedback_ablation and (memory_ablation or retry_memory):
        raise ValueError("Feedback and memory studies must be separate")
    if memory_ablation and (retry_memory or fault != "none"):
        raise ValueError("Memory ablation requires healthy environments and per-arm memory selection")
    arms = (("one_shot", "memory_off", "memory_on") if memory_ablation else
            ("one_shot", "basic_feedback", "operation_feedback") if feedback_ablation else ARMS)
    if feedback_ablation and (fault != "none" or tuple(tasks) != ("commons_cli",)):
        raise ValueError("Feedback ablation requires Commons CLI and a healthy environment")
    if trials < 1 or trials > 100 or not 0 <= max_repairs <= 5:
        raise ValueError("Trials must be 1..100 and repairs 0..5")
    if len(set(tasks)) != len(tasks) or any(t not in suite.identity()["counts"] for t in tasks):
        raise ValueError("Unknown or repeated task")
    planned = [{"trial": trial, "task": task, "arm": arm,
                "path": f"trial-{trial:03}/{task}/{arm}"}
               for trial in range(trials) for task in tasks for arm in arms]
    if budget_policy == "partitioned" and getattr(backend, "budget", None):
        from .budget import PartitionedBudget
        backend.budget = PartitionedBudget(backend.budget, planned, max_repairs, max_output_tokens)
    directory = directory or new_run("experiment")
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(suite.path, directory / "evaluation-suite.json")
    suite = FrozenSuite(directory / "evaluation-suite.json")
    plan = {"schema": 1, "backend": backend.identity, "suite": suite.identity(), "model_request_timeout_seconds": model_timeout,
            "planned_runs": planned, "budget_policy": budget_policy, "arms": arms, "feedback_ablation": feedback_ablation, "memory_ablation": memory_ablation, "retry_memory": retry_memory,
            "arm_order_policy": "Alternate the two repair-arm execution orders by trial" if feedback_ablation or memory_ablation else "Fixed arm order", "runtimes": ["cpython", "graal"], "max_repairs": max_repairs,
            "study": "memory_ablation" if memory_ablation else "feedback_ablation" if feedback_ablation else "natural_translation" if fault == "none" else "controlled_environment_stress",
            "fault": fault, "protected_hashes": protected_hashes(),
            "settings": {"timeout": timeout, "max_seconds": max_seconds,
                         "max_output_tokens": max_output_tokens, "output_token_budget": output_token_budget},
            "pairing": "One fresh initial generation per task/trial, reused verbatim in both repair arms; "
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
                execution_arms = (arms[0], *reversed(arms[1:])) if (feedback_ablation or memory_ablation) and trial % 2 else arms
                for arm in execution_arms:
                    folder = base / arm
                    started = time.monotonic()
                    try:
                        if budget_policy == "partitioned" and getattr(backend, "budget", None):
                            backend.budget.activate(f"trial-{trial:03}/{task}/{arm}")
                        env = EnvironmentAgent(timeout, ContainerExecutor(fault="none" if arm == "one_shot" else fault))
                        environments[str(folder)] = env
                        if arm != "one_shot" and paired is None:
                            raise RuntimeError("Initial generation failed; paired arm remains unvalidated")
                        print(f"Trial {trial + 1}/{trials}: {task}, {arm}", flush=True)
                        run_task(task, backend if arm == "one_shot" else paired,
                                 max_repairs=0 if arm == "one_shot" else max_repairs,
                                 timeout=timeout, model_timeout=model_timeout, max_seconds=max_seconds,
                                 max_output_tokens=max_output_tokens, output_token_budget=output_token_budget,
                                 directory=folder, environment=env, suite=suite,
                                 environment_repairs=arm == "environment_repair", defer_holdout=True,
                                 **({"feedback_mode": "basic" if arm == "basic_feedback" else "operation"} if feedback_ablation else
                                    {"feedback_mode": "pruned", "retry_memory": arm == "memory_on"} if memory_ablation else
                                    {"feedback_mode": "pruned", "retry_memory": arm != "one_shot"} if retry_memory else {}))
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
        aggregate(directory)
    return directory, aggregate(directory)
