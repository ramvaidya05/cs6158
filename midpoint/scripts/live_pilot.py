"""Run a small live study, reading a missing API key without terminal echo or disk storage."""
import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from migration_lab.credentials import load_key
from migration_lab.backends import OpenAIResponsesBackend
from migration_lab.budget import SpendBudget
from migration_lab.experiments import run_experiment, archive_run
from migration_lab.protocol import FrozenSuite


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--max-spend-usd',type=float,default=1.0)
    parser.add_argument('--trials',type=int,default=3)
    parser.add_argument('--input-usd-per-million',type=float,required=True)
    parser.add_argument('--output-usd-per-million',type=float,required=True)
    args=parser.parse_args()
    load_key(prompt=True)
    budget=SpendBudget(args.max_spend_usd,args.input_usd_per_million,args.output_usd_per_million)
    backend=OpenAIResponsesBackend(args.model,'medium',budget)
    try:
        directory,result=run_experiment(backend,FrozenSuite(args.suite),trials=args.trials)
        print(f'Archived: {archive_run(directory)}',flush=True)
        print('Actual model calls:',result['usage']['model_calls'],flush=True)
        print('Conservative accounted spend USD:',round(budget.record()['accounted_usd'],6),flush=True)
        for arm,summary in result['arms'].items():
            print(arm,summary['tasks_passing'],'/',summary['admitted_task_trials'],flush=True)
        return 0 if all(r['status']=='completed' for r in result['runs']) else 1
    finally:
        os.environ.pop('OPENAI_API_KEY',None)


if __name__=='__main__':
    raise SystemExit(main())
