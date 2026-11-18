"""Bounded M/E/T orchestration. Only visible results influence checkpoint selection."""
import time
import json
import math
from .benchmark import cases, verify_vendor
from .environment import EnvironmentAgent
from .evaluation import TestsuiteAgent
from .storage import ROOT, new_run, save_json, sha256, protected_hashes
from .translator import MigrationAgent


def improves_without_regression(current, best):
    if best is None:
        return True
    if current["passed"] <= best["passed"]:
        return False
    return all(set(old["passed_ids"]).issubset(current["runtimes"][mode]["passed_ids"])
               for mode, old in best["runtimes"].items())


def assert_unchanged(original):
    if protected_hashes() != original:
        raise RuntimeError("Protected source/evaluator/context files changed; run invalidated")


def run_task(task, backend, *, max_repairs=5, modes=("cpython", "graal"), seed=6158,
             timeout=60, model_timeout=120, max_seconds=900, max_output_tokens=8192, output_token_budget=49152,
             directory=None, environment=None, suite=None, environment_repairs=False,
             defer_holdout=False, feedback_mode="full", retry_memory=False):
    if feedback_mode not in ("full", "basic", "operation", "pruned"):
        raise ValueError("Unknown feedback mode")
    if not 0 <= max_repairs <= 5:
        raise ValueError("Allowed repair count is 0 through 5")
    if not modes or len(set(modes)) != len(modes) or set(modes) - {"cpython", "graal"}:
        raise ValueError("Choose unique cpython/graal runtime names")
    if any(not math.isfinite(n) or n <= 0 for n in (timeout, model_timeout, max_seconds, max_output_tokens, output_token_budget)):
        raise ValueError("Budgets must be positive")
    verify_vendor()
    directory = directory or new_run(task)
    directory.mkdir(parents=True, exist_ok=True)
    environment = environment or EnvironmentAgent(timeout)
    if backend.identity.get("provenance") == "live_model" and not getattr(environment, "isolated", False):
        raise RuntimeError("Live generated code requires container isolation; local execution refused")
    case_source = suite.cases if suite else cases
    tester = TestsuiteAgent(environment)
    migration = MigrationAgent(backend)
    from .retry_memory import RetryMemory
    memory = RetryMemory(directory) if retry_memory else None
    guard = protected_hashes()
    started = time.monotonic()
    manifest = {"task": task, "backend": backend.identity, "max_repairs": max_repairs,
                "runtimes": list(modes), "seed": seed, "timeout_per_process_seconds": timeout, "model_request_timeout_seconds": model_timeout,
                "max_loop_seconds": max_seconds, "max_output_tokens_per_call": max_output_tokens,
                "output_token_budget": output_token_budget, "protected_hashes": guard,
                "environment": environment.doctor(),
                "evaluation_suite": suite.identity() if suite else {"kind": "public_demo"},
                "environment_repairs": environment_repairs, "feedback_mode": feedback_mode,
                "retry_memory": retry_memory, "dependency_policy": "stdlib-only-v1",
                "child_locale": {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC"},
                "holdout_policy": ("Frozen evaluator-only suite; excluded from model context; scored after selection"
                                   if suite else "Public demo cases; excluded from model context; scored after selection only"),
                "budget_note": "Loop deadline checked between calls; final evaluation may run beyond it. "
                               "Output budget reserves requested maximum per call, not input tokens or dollars."}
    if task == "commons_cli":
        from .cli_task import identity
        manifest["task_contract"] = identity()
    save_json(directory / "manifest.json", manifest)
    state = {"status": "running", "task": task, "provenance": backend.identity["provenance"],
             "environment_actions": [], "events": [],
             "attempts": [], "best_attempt": None, "stop_reason": None}
    def event(phase, **details):
        state["events"].append({"phase": phase, "elapsed_seconds": round(time.monotonic() - started, 3), **details})
        save_json(directory / "result.json", state)
    save_json(directory / "result.json", state)
    try:
        event("preflight")
        probe = [{"id": "preflight", "task": "levenshtein", "a": "", "b": "",
                  "operation": "distance", "parameter": None}]
        for mode in modes:
            check = environment.run(mode, probe, directory / "preflight" / mode,
                                    ROOT / "fixtures/preflight.py")
            if check["status"] != "completed" and environment_repairs and len(state["environment_actions"]) < max_repairs:
                action = environment.remediate(mode, check)
                if action:
                    action["evidence"] = f"preflight/{mode}/execution.json"
                    state["environment_actions"].append(action)
                    event("environment_repair", action=action)
                    check = environment.run(mode, probe, directory / "preflight-repaired" / mode,
                                            ROOT / "fixtures/preflight.py")
            if check["status"] != "completed" or check["rows"][0].get("value") != 0:
                raise RuntimeError(f"Infrastructure preflight failed for {mode}; see preflight artifacts")
        visible = case_source(task, "visible", seed)
        event("reference")
        reference = tester.reference(visible, directory / "reference-visible")
        if suite and reference != suite.reference(task, "visible"):
            raise RuntimeError("Visible oracle differs from frozen protocol")
        repeated = tester.reference(visible, directory / "reference-repeat")
        if reference != repeated:
            raise RuntimeError("Java reference is nondeterministic on visible cases")
        best = best_path = initial_path = None
        previous = feedback = None
        seen = set()
        no_progress = reserved_tokens = 0
        for attempt in range(max_repairs + 1):
            if attempt + len(state["environment_actions"]) > max_repairs:
                state["stop_reason"] = "shared_repair_budget"
                break
            assert_unchanged(guard)
            remaining = max_seconds - (time.monotonic() - started)
            if remaining <= 0:
                state["stop_reason"] = "loop_deadline"
                break
            if reserved_tokens + max_output_tokens > output_token_budget:
                state["stop_reason"] = "output_token_budget"
                break
            folder = directory / "attempts" / f"{attempt:02}"
            folder.mkdir(parents=True)
            prompt = migration.prompt(task, previous, feedback)
            if memory and memory.history:
                prompt += "\n\n" + memory.context()
            (folder / "prompt.txt").write_text(prompt, encoding="utf-8")
            reserved_tokens += max_output_tokens
            state["reserved_output_tokens"] = reserved_tokens
            try:
                event("translate" if attempt == 0 else "code_repair", attempt=attempt)
                response = backend.generate(task, attempt, prompt, timeout=min(model_timeout, remaining),
                                            max_output_tokens=max_output_tokens)
            except Exception as exc:
                save_json(folder / "backend-error.json", {"type": type(exc).__name__, "message": str(exc),
                          "kind": getattr(exc, "kind", "backend_error"), "details": getattr(exc, "details", {}),
                          "raw_response": getattr(exc, "raw_response", None)})
                if best_path is not None:
                    state["attempts"].append({"attempt": attempt, "status": "backend_error", "accepted": False})
                    state["backend_failure"] = {"kind": getattr(exc, "kind", "backend_error"), "message": str(exc)}
                    state["stop_reason"] = "backend_error"
                    event("backend_error", attempt=attempt)
                    break
                raise
            save_json(folder / "response.json", response)
            candidate = folder / "candidate.py"
            candidate.write_text(response["code"], encoding="utf-8")
            from .dependencies import write_requirements
            dependency_report = write_requirements(candidate, folder)
            digest = sha256(candidate)
            if digest in seen:
                state["attempts"].append({"attempt": attempt, "sha256": digest,
                                          "accepted": False, "status": "repeated_candidate"})
                state["stop_reason"] = "repeated_candidate"
                break
            seen.add(digest)
            event("evaluate_visible", attempt=attempt)
            if dependency_report["status"] == "blocked":
                summary = {"passed": 0, "total": len(visible) * len(modes), "all_pass": False,
                    "runtimes": {mode: {"passed": 0, "total": len(visible), "passed_ids": [],
                        "status": "dependency_policy", "failures": [{"kind": "dependency_policy",
                        "detail": json.dumps(dependency_report)}]} for mode in modes}}
                save_json(folder / "visible/summary.json", summary)
            else:
                summary = tester.evaluate(candidate, visible, reference, modes, folder / "visible")
            assert_unchanged(guard)
            if initial_path is None:
                initial_path = candidate
                state["baseline_visible"] = summary
            accepted = improves_without_regression(summary, best)
            if accepted:
                best, best_path = summary, candidate
                state["best_attempt"] = attempt
                no_progress = 0
            else:
                no_progress += 1
            state["attempts"].append({"attempt": attempt, "sha256": digest,
                                      "accepted": accepted, "status": "evaluated",
                                      "passed": summary["passed"], "total": summary["total"]})
            if memory:
                memory.update(attempt, digest, summary, accepted, previous, response["code"])
            event("checkpoint", attempt=attempt, accepted=accepted)
            state["reserved_output_tokens"] = reserved_tokens
            save_json(directory / "result.json", state)
            # Repair from the best checkpoint, never from a rejected regression.
            previous = best_path.read_text(encoding="utf-8")
            feedback = migration.feedback(best) if feedback_mode == "full" else migration.feedback(best, feedback_mode)
            if summary["all_pass"]:
                state["stop_reason"] = "visible_pass"
                break
            if no_progress >= 2:
                state["stop_reason"] = "no_progress"
                break
        state["stop_reason"] = state["stop_reason"] or "attempt_limit"
        if best_path is None:
            raise RuntimeError("No candidate was evaluated within the configured budget")
        final = directory / "final.py"
        final.write_text(best_path.read_text(encoding="utf-8"), encoding="utf-8")
        from .dependencies import write_requirements
        write_requirements(final, directory)
        state["selected_visible"] = best
        # Freeze selection before materializing/scoring holdout. No feedback goes back to M-Agent.
        save_json(directory / "selection.json", {"attempt": state["best_attempt"],
                  "sha256": sha256(final), "selection_inputs": "visible results only"})
        event("selection_frozen")
        state["status"] = "selected"
        if defer_holdout:
            return directory, state
        holdout = case_source(task, "holdout", seed)
        event("evaluate_holdout")
        held_reference = tester.reference(holdout, directory / "reference-holdout")
        if suite and held_reference != suite.reference(task, "holdout"):
            raise RuntimeError("Frozen oracle changed before scoring")
        state["baseline_holdout"] = tester.evaluate(initial_path, holdout, held_reference, modes,
                                                    directory / "holdout-baseline")
        state["selected_holdout"] = tester.evaluate(final, holdout, held_reference, modes,
                                                    directory / "holdout-selected")
        assert_unchanged(guard)
        state["status"] = "completed"
        state["validated"] = best["all_pass"] and state["selected_holdout"]["all_pass"]
    except Exception as exc:
        state["status"] = "error"
        state["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        state["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save_json(directory / "result.json", state)
    return directory, state


def score_selected(directory, environment, suite):
    """Called only after every paired arm has frozen its selection."""
    state = json.loads((directory / "result.json").read_text())
    if state["status"] != "selected":
        return state
    started = time.monotonic()
    manifest = json.loads((directory / "manifest.json").read_text())
    try:
        state.setdefault("events", []).append({"phase": "evaluate_holdout", "elapsed_seconds": state["elapsed_seconds"]})
        assert_unchanged(manifest["protected_hashes"])
        selection = json.loads((directory / "selection.json").read_text())
        final = directory / "final.py"
        if sha256(final) != selection["sha256"]:
            raise RuntimeError("Selected candidate changed before scoring")
        initial = directory / "attempts/00/candidate.py"
        if sha256(initial) != state["attempts"][0]["sha256"]:
            raise RuntimeError("Baseline candidate changed before scoring")
        held = suite.cases(state["task"], "holdout")
        tester = TestsuiteAgent(environment)
        reference = tester.reference(held, directory / "reference-holdout")
        if reference != suite.reference(state["task"], "holdout"):
            raise RuntimeError("Frozen oracle changed before scoring")
        state["baseline_holdout"] = tester.evaluate(initial, held, reference, manifest["runtimes"], directory / "holdout-baseline")
        state["selected_holdout"] = tester.evaluate(final, held, reference, manifest["runtimes"], directory / "holdout-selected")
        state["validated"] = state["selected_visible"]["all_pass"] and state["selected_holdout"]["all_pass"]
        assert_unchanged(manifest["protected_hashes"])
        state["status"] = "completed"
        state["events"].append({"phase": "completed", "elapsed_seconds": state["elapsed_seconds"] + time.monotonic() - started})
    except Exception as exc:
        state["status"] = "error"
        state["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        state["scoring_seconds"] = round(time.monotonic() - started, 3)
        state["elapsed_seconds"] += state["scoring_seconds"]
        save_json(directory / "result.json", state)
    return state
