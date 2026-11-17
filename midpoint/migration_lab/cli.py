import argparse
import json
import sys
from pathlib import Path
from .backends import GeminiBackend, OpenAIResponsesBackend, ReplayBackend
from .benchmark import TASKS, ALL_TASKS, verify_vendor
from .controller import run_task
from .environment import EnvironmentAgent
from .storage import ROOT, new_run, save_json


def main(argv=None):
    parser = argparse.ArgumentParser(description="Midpoint Java-to-Python translation lab")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect local tools; does not install or call a model")
    freeze_parser = commands.add_parser("freeze", help="Freeze evaluator-only inputs and repeated Java oracle outputs")
    freeze_parser.add_argument("--output", type=Path, required=True)
    freeze_parser.add_argument("--seed", type=int)
    freeze_parser.add_argument("--task", choices=(*ALL_TASKS, "all"), default="all")
    report_parser = commands.add_parser("report", help="Recompute failure-inclusive experiment accuracy")
    report_parser.add_argument("directory", type=Path)
    catalog_parser = commands.add_parser("catalog", help="Verify and compare archives without modifying evidence")
    catalog_parser.add_argument("directories", type=Path, nargs="+")
    catalog_parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    catalog_parser.add_argument("--output", type=Path, help="New report outside input archives; refuses overwrite")
    experiment = commands.add_parser("experiment", help="Paired one-shot/code/environment repair trials in containers")
    experiment.add_argument("--suite", type=Path, required=True)
    experiment.add_argument("--task", choices=(*ALL_TASKS, "all"), default="levenshtein")
    experiment.add_argument("--trials", type=int, default=3)
    experiment.add_argument("--backend", choices=("replay", "openai", "gemini"), required=True)
    experiment.add_argument("--replay-manifest", type=Path)
    experiment.add_argument("--model")
    experiment.add_argument("--reasoning-effort", default="medium")
    experiment.add_argument("--max-repairs", type=int, default=5)
    experiment.add_argument("--timeout", type=float, default=60)
    experiment.add_argument("--model-timeout", type=float, default=120, help="Model HTTP socket timeout in seconds, separate from execution timeout")
    experiment.add_argument("--max-seconds", type=float, default=900)
    experiment.add_argument("--max-output-tokens", type=int, default=8192)
    experiment.add_argument("--output-token-budget", type=int, default=49152)
    experiment.add_argument("--max-spend-usd", type=float, default=1.0)
    experiment.add_argument("--input-usd-per-million", type=float)
    experiment.add_argument("--output-usd-per-million", type=float)
    experiment.add_argument("--fault", choices=("none", "graal-cache"), default="none")
    experiment.add_argument("--archive", action="store_true")
    for name in ("demo", "run"):
        p = commands.add_parser(name)
        p.add_argument("--task", choices=(*ALL_TASKS, "all"), default="all")
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
            p.add_argument("--execution", choices=("container", "local"), default="container")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            from .protocol import freeze
            print(json.dumps(freeze(args.output, args.seed, tasks=TASKS if args.task == "all" else (args.task,)).identity(), indent=2))
            return 0
        if args.command == "report":
            from .experiments import aggregate
            from .reporting import inspect_experiment
            result = (inspect_experiment(args.directory)["report"] if (args.directory / "checksums.json").exists()
                      else aggregate(args.directory, persist=False))
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "catalog":
            from .reporting import build_catalog, render_catalog
            if args.output and any(args.output.resolve().is_relative_to(p.resolve()) for p in args.directories):
                parser.error("Catalog output must be outside every input archive")
            catalog = build_catalog(args.directories)
            rendered = json.dumps(catalog, indent=2, allow_nan=False) + "\n" if args.format == "json" else render_catalog(catalog)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("x", encoding="utf-8") as stream:
                    stream.write(rendered)
                print(f"Report: {args.output.resolve()}")
            else:
                print(rendered)
            return 0
        if args.command == "experiment":
            from .budget import SpendBudget
            from .protocol import FrozenSuite
            from .experiments import run_experiment, archive_run
            suite = FrozenSuite(args.suite)
            if args.backend == "replay":
                if not args.replay_manifest:
                    parser.error("Replay requires --replay-manifest")
                backend = ReplayBackend(args.replay_manifest)
            elif args.backend == "gemini":
                from .credentials import load_key
                load_key(provider="gemini")
                if args.input_usd_per_million is None or args.output_usd_per_million is None:
                    parser.error("Supply token prices; on the free tier use the paid rates as a safety cap")
                backend = GeminiBackend(args.model, args.reasoning_effort,
                    SpendBudget(args.max_spend_usd, args.input_usd_per_million, args.output_usd_per_million))
            else:
                from .credentials import load_key
                load_key()
                input_rate, output_rate = args.input_usd_per_million, args.output_usd_per_million
                if args.model == "gpt-5.6-sol":
                    input_rate = input_rate if input_rate is not None else 4.0
                    output_rate = output_rate if output_rate is not None else 20.0
                if input_rate is None or output_rate is None:
                    parser.error("Supply documented input/output token prices for this model")
                backend = OpenAIResponsesBackend(args.model, args.reasoning_effort,
                    SpendBudget(args.max_spend_usd, input_rate, output_rate))
            path, result = run_experiment(backend, suite, tasks=tuple(suite.identity()["counts"]) if args.task == "all" else (args.task,),
                trials=args.trials, max_repairs=args.max_repairs, timeout=args.timeout, model_timeout=args.model_timeout,
                max_seconds=args.max_seconds, max_output_tokens=args.max_output_tokens,
                output_token_budget=args.output_token_budget, fault=args.fault)
            if args.archive:
                print(f"Archived: {archive_run(path)}")
            print(f"Artifacts: {path}")
            print(json.dumps({"arms": result["arms"], "usage": result["usage"]}, indent=2))
            return 0 if all(r["validated"] for r in result["runs"]) else 1
        if args.command == "doctor":
            result = EnvironmentAgent().doctor()
            result["vendor_verified"] = bool(verify_vendor())
            print(json.dumps(result, indent=2))
            return 0
        kwargs = {}
        if args.command == "demo":
            backend = ReplayBackend(ROOT / "fixtures/replay.json")
        else:
            if args.execution == "local" and (args.backend == "openai" or not args.allow_local_execution):
                parser.error("Local execution requires trusted replay and --allow-local-execution; live code requires containers")
            if args.execution == "container":
                from .isolation import ContainerExecutor
                kwargs["environment"] = EnvironmentAgent(args.timeout, ContainerExecutor())
            if args.backend == "openai":
                from .credentials import load_key
                load_key()
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
