"""Measure whether the frozen evaluator detects explicit source-semantic faults.

These are synthetic mutations of hand-authored fixtures, never model results.
All mutations are fixed before scoring; surviving mutations remain recorded.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.controller import assert_unchanged
from migration_lab.environment import EnvironmentAgent
from migration_lab.evaluation import TestsuiteAgent
from migration_lab.experiments import archive_run
from migration_lab.isolation import ContainerExecutor
from migration_lab.protocol import FrozenSuite
from migration_lab.storage import new_run, protected_hashes, save_json, sha256


UNIT_RETURN = 'return [raw[i] + 256 * raw[i + 1] for i in range(0, len(raw), 2)]'
MUTATIONS = (
    ('levenshtein_codepoints', 'levenshtein', UNIT_RETURN, 'return list(s)'),
    ('levenshtein_ignores_limit', 'levenshtein',
     'limit = 2147483647 if parameter is None else parameter', 'limit = 2147483647'),
    ('normalized_codepoints', 'normalized', UNIT_RETURN, 'return list(s)'),
    ('normalized_minimum_length', 'normalized', 'denominator = max(len(a), len(b))',
     'denominator = min(len(a), len(b))'),
    ('jaro_binary64', 'jaro_winkler', 'return struct.unpack("!f", struct.pack("!f", x))[0]', 'return x'),
    ('jaro_prefix_cap_four', 'jaro_winkler', ' * prefix * (1.0 - similarity)',
     ' * min(prefix, 4) * (1.0 - similarity)'),
    ('jaro_fractional_transpositions', 'jaro_winkler',
     'sum(x != y for x, y in zip(first, second)) // 2',
     'sum(x != y for x, y in zip(first, second)) / 2'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, required=True)
    args = parser.parse_args()
    suite = FrozenSuite(args.suite)
    directory = new_run('semantic-sensitivity')
    tasks = ('levenshtein', 'normalized', 'jaro_winkler')
    sources = {task: (ROOT / f'fixtures/{task}.py').read_text() for task in tasks}
    planned = []
    for name, task, before, after in MUTATIONS:
        if sources[task].count(before) != 1:
            raise ValueError(f'Mutation anchor changed: {name}')
        path = directory / 'candidates' / (name + '.py')
        path.parent.mkdir(exist_ok=True)
        path.write_text(sources[task].replace(before, after), encoding='utf-8')
        planned.append({'name': name, 'task': task, 'path': str(path.relative_to(directory)),
                        'before': before, 'after': after, 'sha256': sha256(path)})
    (directory / 'evaluation-suite.json').write_bytes(suite.path.read_bytes())
    suite = FrozenSuite(directory / 'evaluation-suite.json')
    guard = protected_hashes()
    save_json(directory / 'plan.json', {'provenance': 'synthetic_semantic_mutations',
        'suite': suite.identity(), 'mutations': planned, 'protected_hashes': guard,
        'fixture_sha256': {task: sha256(ROOT / f'fixtures/{task}.py') for task in tasks},
        'policy': 'A mutation is detected only by completed runtime results with semantic mismatches. '
                  'Controls must pass first. Survivors are retained; tests and mutations are not tuned after scoring.'})
    state = {'provenance': 'synthetic_semantic_mutations', 'status': 'running',
             'controls': {}, 'mutations': {p['name']: {'status': 'not_run'} for p in planned}}
    save_json(directory / 'summary.json', state)
    tester = TestsuiteAgent(EnvironmentAgent(60, ContainerExecutor()))
    try:
        for task in tasks:
            rows = suite.cases(task, 'visible') + suite.cases(task, 'holdout')
            reference = suite.reference(task, 'visible') + suite.reference(task, 'holdout')
            result = tester.evaluate(ROOT / f'fixtures/{task}.py', rows, reference,
                                     ('cpython', 'graal'), directory / 'controls' / task)
            state['controls'][task] = {k: result[k] for k in ('passed', 'total', 'all_pass')}
            assert_unchanged(guard)
            save_json(directory / 'summary.json', state)
            if not result['all_pass']:
                raise RuntimeError('Control failed; mutation scoring stopped')
        for item in planned:
            task = item['task']
            rows = suite.cases(task, 'visible') + suite.cases(task, 'holdout')
            reference = suite.reference(task, 'visible') + suite.reference(task, 'holdout')
            result = tester.evaluate(directory / item['path'], rows, reference,
                                     ('cpython', 'graal'), directory / 'mutations' / item['name'])
            assert_unchanged(guard)
            scores = {}
            for mode, observed in result['runtimes'].items():
                completed = observed['status'] == 'completed'
                scores[mode] = {'execution_status': observed['status'],
                               'detected': completed and observed['passed'] < observed['total']}
                passed = set(observed['passed_ids'])
                for split in ('visible', 'holdout'):
                    ids = {row['id'] for row in suite.cases(task, split)}
                    scores[mode][split] = {'total': len(ids), 'passed': len(ids & passed),
                                          'mismatched': len(ids - passed) if completed else None}
            state['mutations'][item['name']] = {'task': task, 'status': 'evaluated', 'runtimes': scores}
            save_json(directory / 'summary.json', state)
            print(item['name'], {m: r['detected'] for m, r in scores.items()}, flush=True)
        state['status'] = 'completed'
        state['detected_in_both_runtimes'] = sum(all(r['detected'] for r in m['runtimes'].values())
                                                for m in state['mutations'].values())
        state['admitted_mutations'] = len(planned)
    except Exception as exc:
        state.update(status='error', error={'type': type(exc).__name__, 'message': str(exc)})
    finally:
        save_json(directory / 'summary.json', state)
        print('Archived:', archive_run(directory), flush=True)
    return 0 if state['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
