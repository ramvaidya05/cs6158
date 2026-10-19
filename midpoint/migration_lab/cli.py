import argparse
import json
import sys
from pathlib import Path
from .backends import OpenAIResponsesBackend, ReplayBackend
from .benchmark import TASKS, verify_vendor
from .controller import run_task
from .environment import EnvironmentAgent
from .storage import ROOT, new_run, save_json


def main(argv=None):
    parser = argparse.ArgumentParser(description="Midpoint Java-to-Python translation lab")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect local tools; does not install or call a model")
    for name in ("demo", "run"):
        p = commands.add_parser(name)
        p.add_argument("--task", choices=(*TASKS, "all"), default="all")
        p.add_argument("--runtimes", choices=("cpython", "graal"), nargs="+", default=["cpython", "graal"])
        p.add_argument("--max-repairs", type=int, default=5)
        p.add_argument("--timeout", type=float, default=60)
        p.add_argument("--max-seconds", type=float, default=900)
        p.add_argument("--seed", type=int, default=6158)
        if name == "run":
            p.add_argument("--backend", choices=("replay", "openai"), required=True)
            p.add_argument("--replay-manifest", type=Path)
            p.add_argument("--model", help="Explicit experimental model; no default")
            p.add_argument("--reasoning-effort")
            p.add_argument("--max-output-tokens", type=int, default=8192)
            p.add_argument("--output-token-budget", type=int, default=49152)
            p.add_argument("--allow-local-execution", action="store_true",
                           help="Acknowledge generated code runs without an OS sandbox")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = EnvironmentAgent().doctor()
            result["vendor_verified"] = bool(verify_vendor())
            print(json.dumps(result, indent=2))
            return 0
        kwargs = {}
        if args.command == "demo":
            backend = ReplayBackend(ROOT / "fixtures/replay.json")
        else:
            if not args.allow_local_execution:
                parser.error("run requires --allow-local-execution. Review candidate trust; local execution is NOT sandboxed.")
            if args.backend == "openai":
                backend = OpenAIResponsesBackend(args.model, args.reasoning_effort)
            else:
                if not args.replay_manifest:
                    parser.error("--backend replay requires --replay-manifest")
                backend = ReplayBackend(args.replay_manifest)
            kwargs.update(max_output_tokens=args.max_output_tokens,
                          output_token_budget=args.output_token_budget)
        tasks = TASKS if args.task == "all" else (args.task,)
        batch = new_run("demo" if args.command == "demo" else "experiment")
        summaries = []
        print(f"Artifacts: {batch}", flush=True)
        print(f"Provenance: {backend.identity['provenance']}", flush=True)
        for task in tasks:
            print(f"Running {task}...", flush=True)
            path, result = run_task(task, backend, max_repairs=args.max_repairs, modes=tuple(args.runtimes),
                                   seed=args.seed, timeout=args.timeout, max_seconds=args.max_seconds,
                                   directory=batch / task, **kwargs)
            summary = {"task": task, "status": result["status"], "validated": result["validated"],
                       "provenance": result["provenance"], "attempts": len(result["attempts"]),
                       "stop_reason": result["stop_reason"], "elapsed_seconds": result["elapsed_seconds"]}
            for key in ("baseline_visible", "selected_visible", "baseline_holdout", "selected_holdout"):
                summary[key] = {k: result[key][k] for k in ("passed", "total", "all_pass")}
            summaries.append(summary)
            save_json(batch / "summary.json", summaries)
            print(json.dumps(summary, indent=2), flush=True)
        return 0 if all(r["validated"] for r in summaries) else 1
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
