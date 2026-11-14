"""Run a small live study, reading a missing API key without terminal echo or disk storage."""
import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from migration_lab.credentials import load_key, PROVIDERS
from migration_lab.backends import OpenAIResponsesBackend, GeminiBackend
from migration_lab.benchmark import TASKS
from migration_lab.budget import SpendBudget
from migration_lab.experiments import run_experiment, archive_run
from migration_lab.protocol import FrozenSuite


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--backend',choices=PROVIDERS,default='openai')
    task_group=parser.add_mutually_exclusive_group()
    task_group.add_argument('--task',choices=(*TASKS, 'all'),default='levenshtein')
    task_group.add_argument('--tasks',choices=TASKS,nargs='+',help='Fixed subset admitted before generation')
    parser.add_argument('--fault',choices=('none','graal-cache'),default='none')
    parser.add_argument('--reasoning-effort',default='medium')
    parser.add_argument('--max-output-tokens',type=int,default=8192)
    parser.add_argument('--output-token-budget',type=int,default=49152)
    parser.add_argument('--max-spend-usd',type=float,default=1.0)
    parser.add_argument('--trials',type=int,default=3)
    parser.add_argument('--input-usd-per-million',type=float,required=True)
    parser.add_argument('--output-usd-per-million',type=float,required=True)
    args=parser.parse_args()
    suite=FrozenSuite(args.suite)
    load_key(prompt=True,provider=args.backend)
    budget=SpendBudget(args.max_spend_usd,args.input_usd_per_million,args.output_usd_per_million)
    backend_type=GeminiBackend if args.backend=='gemini' else OpenAIResponsesBackend
    backend=backend_type(args.model,args.reasoning_effort,budget)
    try:
        directory,result=run_experiment(backend,suite,trials=args.trials,
            tasks=args.tasks or (TASKS if args.task=='all' else (args.task,)),fault=args.fault,
            max_output_tokens=args.max_output_tokens,output_token_budget=args.output_token_budget)
        print(f'Archived: {archive_run(directory)}',flush=True)
        print('Actual model calls:',result['usage']['model_calls'],flush=True)
        print('Conservative accounted spend USD:',round(budget.record()['accounted_usd'],6),flush=True)
        for arm,summary in result['arms'].items():
            print(arm,summary['tasks_passing'],'/',summary['admitted_task_trials'],flush=True)
        return 0 if all(r['status']=='completed' for r in result['runs']) else 1
    finally:
        os.environ.pop(PROVIDERS[args.backend][0],None)


if __name__=='__main__':
    raise SystemExit(main())
