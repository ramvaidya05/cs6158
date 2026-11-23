"""One visible-only repair continuation with trusted runtime diagnosis."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from migration_lab.storage import ROOT, new_run, save_json, sha256
from migration_lab.environment import EnvironmentAgent
from migration_lab.isolation import ContainerExecutor
from migration_lab.runtime_diagnosis import diagnose
from migration_lab.reporting import verify_archive
from migration_lab.experiments import archive_run
from migration_lab.backends import BackendError, GeminiBackend
from migration_lab.budget import SpendBudget
from migration_lab.credentials import load_key
from scripts.validator_luhn_pilot import prompt, score, verify_source

PARENT = ROOT / 'evidence/20261121T232609Z-validator-luhn-pilot'


def repair_prompt(previous, visible, diagnosis):
    failures = [failure for mode in ('cpython', 'graal') for failure in visible[mode]['failures']]
    return prompt(previous, failures) + (
        '\nTrusted environment diagnosis (no evaluation inputs):\n' + json.dumps(diagnosis) +
        '\nUse portable operations. java_decimal_bases was exhaustively checked against all Java char values: '
        'each base begins ten consecutive decimal digits 0..9; all other char values are not decimal digits. '
        'You may embed these bases. Preserve UTF-16 behavior and all previously passing visible cases.')


def accepts(baseline, proposed):
    before = {m: set(baseline[m]['passed_ids']) for m in ('cpython', 'graal')}
    after = {m: set(proposed[m]['passed_ids']) for m in before}
    return (all(proposed[m]['status'] == 'completed' and before[m] <= after[m] for m in before)
            and any(before[m] < after[m] for m in before))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Make the separately authorized single repair call')
    args = parser.parse_args()
    verify_source()
    verified = verify_archive(PARENT)
    parent_result = json.loads((PARENT / 'summary.json').read_text())
    directory = new_run('validator-runtime-repair')
    started = time.monotonic()
    result = {'status': 'started', 'parent': PARENT.name, 'parent_verification': verified,
              'independent_trial': False, 'model_calls': 0, 'manual_candidate_edits': False}
    budget = SpendBudget(min(0.10, 0.15 - parent_result['usage']['accounted_usd']), 1.5, 9.0, directory / 'spend.json')
    try:
        environment = EnvironmentAgent(60, ContainerExecutor())
        diagnosis = diagnose(environment, directory / 'diagnosis')
        baseline = PARENT / 'candidate-0.py'
        visible = json.loads((PARENT / 'attempt-0/visible/score.json').read_text())
        question = repair_prompt(baseline.read_text(), visible, diagnosis)
        save_json(directory / 'prompt.json', {'prompt': question})
        reservation = len(question.encode('utf-8')) + 1024 + 4096
        save_json(directory / 'plan.json', {'model': 'gemini-3.5-flash', 'thinking': 'low',
                  'max_calls': 1, 'max_output_tokens': 4096, 'token_reservation_cap': 20000,
                  'reserved_tokens': reservation, 'usd_cap': budget.limit,
                  'selection': 'strict visible improvement without per-case regressions in either runtime',
                  'holdout_role': 'previously evaluated regression suite; not fresh holdout',
                  'suite_sha256': sha256(PARENT / 'frozen-suite.json')})
        if reservation > 20000:
            raise RuntimeError('Continuation token reservation cap exceeded')
        if not args.live:
            result['status'] = 'prepared'
        else:
            load_key(provider='gemini')
            result['model_calls'] = 1
            response = GeminiBackend('gemini-3.5-flash', 'low', budget).generate(
                'commons_validator_luhn', 2, question, timeout=60, max_output_tokens=4096)
            save_json(directory / 'response.json', response)
            candidate = directory / 'candidate.py'
            candidate.write_text(response['code'])
            suite = json.loads((PARENT / 'frozen-suite.json').read_text())
            proposed = score(environment, candidate, suite['cases']['visible'], suite['reference']['visible'], 'visible', directory)
            result['accepted'] = accepts(visible, proposed)
            result['visible'] = proposed
            selected = candidate if result['accepted'] else baseline
            result['selected_sha256'] = sha256(selected)
            (directory / 'selected.py').write_text(selected.read_text())
            result['regression'] = score(environment, selected, suite['cases']['holdout'], suite['reference']['holdout'], 'regression', directory)
            result['status'] = 'evaluated'
    except BackendError as exc:
        result.update(status='model_error', error={'kind': exc.kind, 'message': str(exc), 'details': exc.details})
    except Exception as exc:
        result.update(status='failed', error={'type': type(exc).__name__, 'message': str(exc)})
    finally:
        os.environ.pop('GEMINI_API_KEY', None)
        result['usage'] = budget.record()
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        save_json(directory / 'summary.json', result)
        print('Archive:', archive_run(directory))
    print('Status:', result['status'], 'Accepted:', result.get('accepted'))
    for split in ('visible', 'regression'):
        print(split, {m: (v['passed'], v['total']) for m,v in result.get(split, {}).items()})
    return 0 if result['status'] in ('prepared', 'evaluated') else 1

if __name__ == '__main__':
    raise SystemExit(main())
