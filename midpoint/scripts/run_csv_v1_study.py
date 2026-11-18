"""Explicit staged live CSV v1 study; frozen suite and independent phase budgets."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.backends import GeminiBackend
from migration_lab.budget import SpendBudget
from migration_lab.controller import run_task
from migration_lab.environment import EnvironmentAgent
from migration_lab.experiments import run_experiment, archive_run
from migration_lab.isolation import ContainerExecutor
from migration_lab.protocol import FrozenSuite
from migration_lab.storage import new_run, save_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('smoke', 'main', 'memory'), required=True)
    parser.add_argument('--suite', type=Path, required=True)
    args = parser.parse_args()
    suite = FrozenSuite(args.suite)
    if suite.identity()['profile'] != 'commons-csv-v1':
        raise ValueError('The predeclared CSV v1 profile is required')
    from migration_lab.credentials import load_key, validate_key
    # Retain the user's established .env setup; the merged loader defaults to .env.gemini.
    if not os.environ.get('GEMINI_API_KEY') and not (ROOT/'.env.gemini').exists() and (ROOT/'.env').exists():
        for line in (ROOT/'.env').read_text().splitlines():
            name, separator, value = line.partition('=')
            if separator and name.strip() == 'GEMINI_API_KEY':
                os.environ['GEMINI_API_KEY'] = validate_key(value.strip().strip('"\''), 'gemini')
    load_key(provider='gemini')
    budget = SpendBudget(.4 if args.phase == 'smoke' else 8, .75, 3.75)
    backend = GeminiBackend('gemini-3.8-flash', 'low', budget)
    directory = new_run('csv-v1-' + args.phase)
    save_json(directory / 'stage.json', {'phase':args.phase, 'purpose':'live smoke; excluded from cohorts' if args.phase=='smoke' else 'three fresh paired trials',
        'rates_note':'Supplied conservative accounting rates; not a provider invoice or verified current price',
        'model':'gemini-3.8-flash','max_repairs':0 if args.phase=='smoke' else 3,
        'budget_limit_usd':budget.limit,'fault':'none','memory_enabled':args.phase=='memory',
        'policy':'No cross-trial learning or manual candidate edits. All selections before holdout scoring.'})
    print('Artifacts:',directory,flush=True)
    try:
        settings = dict(timeout=90, model_timeout=300, max_seconds=1200,
                        max_output_tokens=32768, output_token_budget=131072)
        if args.phase == 'smoke':
            shutil.copyfile(suite.path,directory/'evaluation-suite.json')
            budget.path=directory/'spend.json'
            budget.record()
            _, result = run_task('commons_csv',backend,max_repairs=0,directory=directory,
                suite=FrozenSuite(directory/'evaluation-suite.json'),
                environment=EnvironmentAgent(90,ContainerExecutor()),**settings)
            save_json(directory/'smoke-summary.json', {k:result.get(k) for k in ('status','validated','stop_reason','selected_visible','selected_holdout')})
            print('Smoke:', result['status'], 'validated=',result.get('validated'),flush=True)
        else:
            _, result = run_experiment(backend,suite,tasks=('commons_csv',),trials=3,max_repairs=3,
                directory=directory,memory_ablation=args.phase=='memory',budget_policy='partitioned',**settings)
            print(json.dumps({'arms':result['arms'],'usage':result['usage']},indent=2),flush=True)
    finally:
        budget = backend.budget
        if budget.path: budget.record()
        print('Archived:',archive_run(directory),flush=True)


if __name__ == '__main__':
    main()
