"""Audit declared API exercise against archived Java traces; no model calls."""
import argparse
import hashlib
import json
from pathlib import Path


def audit(contract, suite):
    classes = contract['classes']
    signatures = {f'{cls}.{method}': spec for cls, definition in classes.items()
                  for method, spec in definition['methods'].items()}
    constructors = {f'{cls}.__init__': definition['constructor'] for cls, definition in classes.items()
                    if 'constructor' in definition}
    splits = {}
    for split, data in suite['tasks']['commons_cli'].items():
        counts = {key: dict(scheduled=0, reached=0, normal=0, exception=0)
                  for key in {**signatures, **constructors}}
        references = {row['id']: row for row in data['reference']}
        for case in data['cases']:
            handles = {}
            trace = {row['step']: row for row in references[case['id']]['trace']}
            for step, op in enumerate(case['operations']):
                if op['op'] == 'new':
                    cls = op['class']
                    key = f'{cls}.__init__'
                    handles[op['save']] = cls
                else:
                    cls = handles[op['on']]
                    key = f"{cls}.{op['method']}"
                    returns = signatures[key]['returns']
                    if op.get('save') and returns in classes:
                        handles[op['save']] = returns
                counts[key]['scheduled'] += 1
                if step in trace:
                    counts[key]['reached'] += 1
                    counts[key]['normal' if trace[step]['status'] == 'ok' else 'exception'] += 1
        splits[split] = {'cases': len(data['cases']), 'api': counts,
                         'methods_reached': sum(counts[key]['reached'] > 0 for key in signatures),
                         'methods_with_normal_return': sum(counts[key]['normal'] > 0 for key in signatures)}
    return {'source_artifact': contract['source_artifact'], 'classes': len(classes),
            'method_signatures': len(signatures), 'constructor_signatures': len(constructors),
            'source_context_files': len(contract['source_files']), 'splits': splits,
            'excluded': contract['excluded'], 'candidate_scope': contract['candidate_scope'],
            'limitation': 'Reference trace API exercise only; not candidate correctness, branch/line coverage, '
                          'all upstream overloads, or full repository translation. Void returns alone do not prove state updates.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = Path(__file__).resolve().parents[1] / 'benchmarks/commons_cli.json'
    result = audit(json.loads(manifest.read_text()), json.loads(args.suite.read_text()))
    result['sha256'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                        for name, path in [('suite', args.suite), ('contract', manifest), ('audit_script', Path(__file__))]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'splits'}, indent=2))


if __name__ == '__main__':
    main()
