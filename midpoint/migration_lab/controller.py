"""Bounded M/E/T orchestration. Only visible results influence checkpoint selection."""
import time
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
             timeout=60, max_seconds=900, max_output_tokens=8192, output_token_budget=49152,
             directory=None):
    if not 0 <= max_repairs <= 5:
        raise ValueError("Allowed repair count is 0 through 5")
    if not modes or len(set(modes)) != len(modes) or set(modes) - {"cpython", "graal"}:
        raise ValueError("Choose unique cpython/graal runtime names")
    if min(timeout, max_seconds, max_output_tokens, output_token_budget) <= 0:
        raise ValueError("Budgets must be positive")
    verify_vendor()
    directory = directory or new_run(task)
    directory.mkdir(parents=True, exist_ok=True)
    environment = EnvironmentAgent(timeout)
    tester = TestsuiteAgent(environment)
    migration = MigrationAgent(backend)
    guard = protected_hashes()
    started = time.monotonic()
    manifest = {"task": task, "backend": backend.identity, "max_repairs": max_repairs,
                "runtimes": list(modes), "seed": seed, "timeout_per_process_seconds": timeout,
                "max_loop_seconds": max_seconds, "max_output_tokens_per_call": max_output_tokens,
                "output_token_budget": output_token_budget, "protected_hashes": guard,
                "environment": environment.doctor(),
                "child_locale": {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC"},
                "holdout_policy": "Public demo cases; excluded from model context; scored after selection only",
                "budget_note": "Loop deadline checked between calls; final evaluation may run beyond it. "
                               "Output budget reserves requested maximum per call, not input tokens or dollars."}
    save_json(directory / "manifest.json", manifest)
    state = {"status": "running", "task": task, "provenance": backend.identity["provenance"],
             "attempts": [], "best_attempt": None, "stop_reason": None}
    save_json(directory / "result.json", state)
    try:
        probe = [{"id": "preflight", "task": "levenshtein", "a": "", "b": "",
                  "operation": "distance", "parameter": None}]
        for mode in modes:
            check = environment.run(mode, probe, directory / "preflight" / mode,
                                    ROOT / "fixtures/preflight.py")
            if check["status"] != "completed" or check["rows"][0].get("value") != 0:
                raise RuntimeError(f"Infrastructure preflight failed for {mode}; see preflight artifacts")
        visible = cases(task, "visible", seed)
        reference = tester.reference(visible, directory / "reference-visible")
        repeated = tester.reference(visible, directory / "reference-repeat")
        if reference != repeated:
            raise RuntimeError("Java reference is nondeterministic on visible cases")
        best = best_path = initial_path = None
        previous = feedback = None
        seen = set()
        no_progress = reserved_tokens = 0
        for attempt in range(max_repairs + 1):
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
            (folder / "prompt.txt").write_text(prompt, encoding="utf-8")
            reserved_tokens += max_output_tokens
            try:
                response = backend.generate(task, attempt, prompt, timeout=min(120, remaining),
                                            max_output_tokens=max_output_tokens)
            except Exception as exc:
                save_json(folder / "backend-error.json", {"type": type(exc).__name__, "message": str(exc),
                          "raw_response": getattr(exc, "raw_response", None)})
                raise
            save_json(folder / "response.json", response)
            candidate = folder / "candidate.py"
            candidate.write_text(response["code"], encoding="utf-8")
            digest = sha256(candidate)
            if digest in seen:
                state["attempts"].append({"attempt": attempt, "sha256": digest,
                                          "accepted": False, "status": "repeated_candidate"})
                state["stop_reason"] = "repeated_candidate"
                break
            seen.add(digest)
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
            state["reserved_output_tokens"] = reserved_tokens
            save_json(directory / "result.json", state)
            # Repair from the best checkpoint, never from a rejected regression.
            previous = best_path.read_text(encoding="utf-8")
            feedback = migration.feedback(best)
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
        state["selected_visible"] = best
        # Freeze selection before materializing/scoring holdout. No feedback goes back to M-Agent.
        save_json(directory / "selection.json", {"attempt": state["best_attempt"],
                  "sha256": sha256(final), "selection_inputs": "visible results only"})
        holdout = cases(task, "holdout", seed)
        held_reference = tester.reference(holdout, directory / "reference-holdout")
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
