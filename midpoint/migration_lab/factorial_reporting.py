"""Descriptive within-trial contrasts; incomplete studies never imply success rates."""
ARMS = ('code_only', 'diagnosis_only', 'semantics_only', 'both')


def summarize(study):
    trials = study.get('trials', [])
    complete = [t for t in trials if all('full_pass' in t.get('arms', {}).get(a, {}) for a in ARMS)]
    result = {'status': study['status'], 'planned_trials': 4,
              'completed_pairs': len(complete), 'incomplete_pairs': len(trials)-len(complete),
              'arms': {}, 'contrasts': [],
              'accounted_usd': sum(b['accounted_usd'] for b in study.get('budgets', [])),
              'tokens': sum(c.get('usage', {}).get('input_tokens', 0) + c.get('usage', {}).get('output_tokens', 0)
                            for b in study.get('budgets', []) for c in b['calls']),
              'elapsed_seconds': study.get('elapsed_seconds')}
    for arm in ARMS:
        result['arms'][arm] = {'full_passes': sum(t['arms'][arm]['full_pass'] for t in complete),
                               'completed_trials': len(complete), 'holdout': {}}
        for mode in ('cpython', 'graal'):
            result['arms'][arm]['holdout'][mode] = {
                key: sum(t['arms'][arm]['holdout'][mode][key] for t in complete)
                for key in ('passed', 'total')}
    for trial in complete:
        y = {a: int(trial['arms'][a]['full_pass']) for a in ARMS}
        result['contrasts'].append({'trial': trial['trial'],
            'diagnosis_minus_control': y['diagnosis_only']-y['code_only'],
            'semantics_minus_control': y['semantics_only']-y['code_only'],
            'both_minus_diagnosis': y['both']-y['diagnosis_only'],
            'both_minus_semantics': y['both']-y['semantics_only'],
            'interaction': y['both']-y['diagnosis_only']-y['semantics_only']+y['code_only']})
    return result
