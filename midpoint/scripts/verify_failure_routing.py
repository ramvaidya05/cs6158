"""Exercise failure routing with controlled candidates in both isolated runtimes.

Synthetic faults qualify the classifier boundary; they are not model results.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.environment import EnvironmentAgent
from migration_lab.evaluation import TestsuiteAgent
from migration_lab.experiments import archive_run
from migration_lab.isolation import ContainerExecutor
from migration_lab.protocol import FrozenSuite
from migration_lab.storage import new_run, save_json, sha256


def classify(preflight, execution, comparison=None):
    """Use trusted probe evidence before assigning a fault to generated code."""
    if preflight['status'] != 'completed' or preflight['rows'][0].get('value') != 0:
        return 'environment'
    if execution['status'] == 'syntax_error':
        return 'candidate_syntax'
    if execution['status'] == 'completed' and any(row['status'] == 'exception' for row in execution['rows']):
        return 'candidate_exception'
    if comparison and not comparison['all_pass']:
        return 'candidate_semantics'
    if execution['status'] == 'completed':
        return 'pass'
    return 'unresolved'


def main():
    suite = FrozenSuite(ROOT / 'evaluator-private/integrated-strings-v2.json')
    directory = new_run('failure-routing')
    case = next(c for c in suite.cases('levenshtein', 'visible') if c['a'] == 'kitten' and c['b'] == 'sitting')
    reference = next(r for r in suite.reference('levenshtein', 'visible') if r['id'] == case['id'])
    save_json(directory / 'plan.json', {'provenance': 'synthetic_fault_injection',
        'suite_sha256': suite.digest, 'case_id': case['id'], 'expected_routes': {
            'healthy': 'pass', 'syntax': 'candidate_syntax',
            'exception': 'candidate_exception', 'wrong_value': 'candidate_semantics',
            'cache_denial': 'environment', 'cache_repaired': 'pass'},
        'notes': 'One predeclared Java-oracle case per runtime; not a translation accuracy study.'})
    candidates = {
        'healthy': 'def run(a, b, operation="distance", parameter=None):\n    return 3\n',
        'syntax': 'def run(:\n    pass\n',
        'exception': 'def run(a, b, operation="distance", parameter=None):\n    import absent_fault_probe_module\n',
        'wrong_value': 'def run(a, b, operation="distance", parameter=None):\n    return 0\n',
    }
    for name, code in candidates.items():
        (directory / (name + '.py')).write_text(code)
    state = {'status': 'running', 'observations': {},
             'candidate_hashes': {n: sha256(directory / (n + '.py')) for n in candidates}}
    save_json(directory / 'summary.json', state)
    try:
        for mode in ('cpython', 'graal'):
            env = EnvironmentAgent(60, ContainerExecutor())
            tester = TestsuiteAgent(env)
            probe_case = [{'id': 'preflight', 'task': 'levenshtein', 'a': '', 'b': '',
                           'operation': 'distance', 'parameter': None}]
            probe = env.run(mode, probe_case, directory / mode / 'probe', ROOT / 'fixtures/preflight.py')
            if probe['status'] != 'completed' or probe['rows'][0].get('value') != 0:
                raise RuntimeError(f'Healthy {mode} probe failed')
            for name in candidates:
                execution = env.run(mode, [case], directory / mode / name, directory / (name + '.py'))
                comparison = (tester.evaluate(directory / (name + '.py'), [case], [reference],
                              (mode,), directory / mode / (name + '-comparison'))
                              if name in ('healthy', 'wrong_value') else None)
                state['observations'][f'{mode}/{name}'] = {'route': classify(probe, execution, comparison),
                    'execution_status': execution['status'],
                    'comparison_passed': comparison['all_pass'] if comparison else None}
                save_json(directory / 'summary.json', state)
            faulty = EnvironmentAgent(60, ContainerExecutor(fault='graal-cache'))
            if mode == 'graal':
                denied = faulty.run(mode, probe_case, directory / mode / 'cache-denial', ROOT / 'fixtures/preflight.py')
                state['observations'][f'{mode}/cache_denial'] = {'route': classify(denied, denied),
                    'execution_status': denied['status']}
                action = faulty.remediate(mode, denied)
                if not action:
                    raise RuntimeError('Trusted cache failure did not produce a bounded remediation')
                repaired = faulty.run(mode, probe_case, directory / mode / 'cache-repaired', ROOT / 'fixtures/preflight.py')
                state['observations'][f'{mode}/cache_repaired'] = {'route': classify(repaired, repaired),
                    'execution_status': repaired['status'], 'action': action}
                save_json(directory / 'summary.json', state)
        expected = {'healthy': 'pass', 'syntax': 'candidate_syntax',
                    'exception': 'candidate_exception', 'wrong_value': 'candidate_semantics'}
        for name, route in expected.items():
            for mode in ('cpython', 'graal'):
                if state['observations'][f'{mode}/{name}']['route'] != route:
                    raise RuntimeError(f'Incorrect routing for {mode}/{name}')
        if (state['observations']['graal/cache_denial']['route'] != 'environment' or
                state['observations']['graal/cache_repaired']['route'] != 'pass'):
            raise RuntimeError('Incorrect cache-failure routing')
        state['status'] = 'passed'
    except Exception as exc:
        state['status'] = 'failed'
        state['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        save_json(directory / 'summary.json', state)
        print('Archived:', archive_run(directory), flush=True)
        print('Outcome:', state['status'], state['observations'], flush=True)
    return 0 if state['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
