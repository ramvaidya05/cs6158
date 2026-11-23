"""Compare full and compact guided CLI prompts on one frozen suite."""
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
from migration_lab.controller import run_task, score_selected
from migration_lab.credentials import load_key, validate_key
from migration_lab.environment import EnvironmentAgent
from migration_lab.experiments import archive_run, usage_at
from migration_lab.isolation import ContainerExecutor
from migration_lab.protocol import FrozenSuite
from migration_lab.storage import new_run, save_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, required=True)
    args = parser.parse_args()
    suite = FrozenSuite(args.suite)
    if suite.identity()['profile'] != 'commons-cli-lookup-v4':
        raise ValueError('CLI v4 suite required')
    if not os.environ.get('GEMINI_API_KEY') and not (ROOT / '.env.gemini').exists():
        for line in (ROOT / '.env').read_text().splitlines():
            name, sep, value = line.partition('=')
            if sep and name.strip() == 'GEMINI_API_KEY':
                os.environ['GEMINI_API_KEY'] = validate_key(value.strip().strip('\"\x27'), 'gemini')
    load_key(provider='gemini')
    environment = EnvironmentAgent(90, ContainerExecutor())
    root = new_run('cli-v4-context')
    print(root, flush=True)
    shutil.copyfile(suite.path, root / 'evaluation-suite.json')
    plan = [(trial, arm) for trial in range(3) for arm in (
        ('full', 'compact_guided') if trial % 2 == 0 else ('compact_guided', 'full'))]
    save_json(root / 'study.json', {'plan': plan, 'suite': suite.identity(), 'model': 'gemini-3.8-flash',
        'thinking': 'low', 'max_repairs': 0, 'max_output_tokens': 32768,
        'per_call_accounting_cap_usd': .38, 'total_accounting_cap_usd': 2.28,
        'policy': 'Independent calls in alternating blocks. Score holdout only after all six selections.'})
    try:
        folders = []
        for trial, arm in plan:
            folder = root / f'trial-{trial}' / arm
            folder.mkdir(parents=True)
            budget = SpendBudget(.38, .75, 3.75, folder / 'spend.json')
            budget.record()
            backend = GeminiBackend('gemini-3.8-flash', 'low', budget)
            print(trial, arm, flush=True)
            run_task('commons_cli', backend, suite=suite, directory=folder,
                environment=environment, max_repairs=0, defer_holdout=True,
                compact_cli=arm == 'compact_guided', timeout=90, model_timeout=300,
                max_seconds=1200, max_output_tokens=32768, output_token_budget=32768)
            folders.append((trial, arm, folder))
        save_json(root / 'selection-barrier.json', [str(folder.relative_to(root)) for _, _, folder in folders])
        rows = []
        for trial, arm, folder in folders:
            state = score_selected(folder, environment, suite)
            scores = {}
            for split in ('visible', 'holdout'):
                scores[split] = {k: {key: v[key] for key in ('passed', 'total', 'status')}
                    for k, v in state.get('selected_' + split, {}).get('runtimes', {}).items()}
            rows.append({'trial': trial, 'arm': arm, 'status': state['status'],
                'validated': state.get('validated', False), 'scores': scores,
                'usage': usage_at(folder), 'elapsed_seconds': state.get('elapsed_seconds'),
                'accounted_usd': json.loads((folder / 'spend.json').read_text())['accounted_usd']})
        save_json(root / 'summary.json', rows)
    finally:
        print('Archived:', archive_run(root), flush=True)


if __name__ == '__main__':
    main()
