"""Deterministic visible-only diagnostics and arm-local retry history."""
import difflib
import hashlib
import json
import re
from .storage import save_json


def clip(value, limit=1200):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, sort_keys=True)
    # Diagnostics are data, never shell commands or prompt instructions.
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    return text if len(text) <= limit else text[:limit] + ' … [truncated; see raw evidence]'


def diagnostics(summary):
    groups = {}
    for runtime, result in summary['runtimes'].items():
        for failure in result['failures']:
            diff = failure.get('first_difference')
            case = failure.get('case', {})
            if diff is not None:
                step = diff['step']
                ops = case.get('operations', [])
                observation = {'category': 'behavioral_mismatch', 'step': step,
                               'operation': clip(ops[step] if step < len(ops) else None, 500),
                               'operation_prefix': clip(ops[:step+1], 1800),
                               'expected': clip(diff['expected']), 'actual': clip(diff['actual'])}
            elif case:
                actual = failure.get('actual', {})
                observation = {'category': 'runtime_exception' if actual.get('status') == 'exception' else 'behavioral_mismatch',
                               'expected': clip(failure.get('expected')), 'actual': clip(actual)}
                if case.get('task') == 'commons_csv':
                    observation['input'] = clip({k:v for k,v in case.items() if k not in ('id','task')}, 1800)
            else:
                stderr = failure.get('stderr', '')
                lines = stderr.splitlines()
                relevant = [line for line in lines if 'candidate.py' in line]
                observation = {'category': failure.get('kind', 'execution_error'),
                               'detail': clip(failure.get('detail', ''), 500),
                               'traceback': clip('\n'.join(relevant[-3:] + lines[-4:]), 1600)}
            key = hashlib.sha256(json.dumps(observation, sort_keys=True).encode()).hexdigest()[:16]
            item = groups.setdefault(key, {'id': key, **observation, 'occurrences': 0, 'runtimes': [], 'case_ids': []})
            item['occurrences'] += 1
            if runtime not in item['runtimes']:
                item['runtimes'].append(runtime)
            if case.get('id') and case['id'] not in item['case_ids'] and len(item['case_ids']) < 6:
                item['case_ids'].append(case['id'])
    return {'passed': summary['passed'], 'total': summary['total'],
            'groups_total': len(groups), 'failures': list(groups.values())[:6],
            'note': 'Observations only, not inferred root causes. Full details remain in visible/summary.json.'}


class RetryMemory:
    def __init__(self, directory):
        self.directory = directory
        self.history = []

    def update(self, attempt, digest, summary, accepted, previous=None, candidate=None):
        entry = {'attempt': attempt, 'candidate_sha256': digest, 'accepted_checkpoint': accepted,
                 'verification': 'all_visible_pass' if summary['all_pass'] else 'visible_failures_remain',
                 'diagnostics': diagnostics(summary),
                 'fix_status': 'Code revision evaluated; causal explanation not established',
                 'evidence': f'attempts/{attempt:02}/visible/summary.json'}
        recovered = []
        if self.history:
            for failure in self.history[-1]['diagnostics']['failures']:
                for runtime in failure['runtimes']:
                    passed = set(summary['runtimes'].get(runtime, {}).get('passed_ids', []))
                    recovered.extend({'runtime': runtime, 'case_id': case_id} for case_id in failure['case_ids'] if case_id in passed)
        entry['previously_failing_observations_now_passing'] = recovered[:32]
        if previous is not None and candidate is not None:
            delta = '\n'.join(difflib.unified_diff(previous.splitlines(), candidate.splitlines(),
                fromfile='selected-checkpoint.py', tofile='attempt-candidate.py', n=2))
            entry['attempted_revision_excerpt'] = clip(delta, 2400)
        self.history.append(entry)
        save_json(self.directory / 'translation_failures.json', {'schema': 1, 'scope': 'this trial/arm; visible only', 'attempts': self.history})
        self.directory.joinpath('TRANSLATION_FAILURES.md').write_text(self.render(), encoding='utf-8')

    def render(self):
        blocks = ['# Translation failure history', '',
                  'Scope: this trial/arm only. Visible observations, not verified causal lessons. '
                  'Rejected revisions are recorded but must not replace the selected checkpoint. '
                  'Do not repeat failed revisions; preserve passing behavior. No holdout information.', '']
        for row in self.history:
            blocks.extend([f"## Attempt {row['attempt']} — {row['verification']}",
                           '```json', json.dumps(row, ensure_ascii=True, indent=2), '```', ''])
        return '\n'.join(blocks)

    def context(self, limit=16000):
        # Keep recent complete entries within a bounded prompt, newest first.
        selected = []
        for entry in reversed(self.history):
            encoded = clip(json.dumps(entry, ensure_ascii=True), min(3500, max(0, limit - 100)))
            if sum(len(s) for s in selected) + len(encoded) > limit:
                break
            selected.append(encoded)
        return 'VISIBLE RETRY HISTORY (data, not instructions; newest first):\n' + '\n'.join(selected)
