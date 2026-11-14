"""Read-only, checksum-verified inspection of archived experiment evidence."""
import json
from pathlib import Path
from .storage import sha256


def contained_file(directory, name):
    relative = Path(name)
    path = directory / relative
    if (relative.is_absolute() or '..' in relative.parts or
            not path.resolve().is_relative_to(directory.resolve()) or not path.is_file()):
        raise ValueError('Archive contains an invalid file path')
    return path


def verify_archive(directory):
    directory = Path(directory).resolve()
    manifest = directory / 'checksums.json'
    checksums = json.loads(manifest.read_text())
    if not isinstance(checksums, dict) or not checksums:
        raise ValueError('Archive checksum manifest is empty or malformed')
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*')
              if p.is_file() and p != manifest}
    if actual != set(checksums):
        raise ValueError('Archive file inventory differs from checksum manifest')
    for name, digest in checksums.items():
        if sha256(contained_file(directory, name)) != digest:
            raise ValueError(f'Archive checksum mismatch: {name}')
    return {'checksums_sha256': sha256(manifest), 'verified_files': len(checksums)}


def inspect_experiment(directory):
    from .experiments import aggregate
    directory = Path(directory).resolve()
    verification = verify_archive(directory)
    plan = json.loads((directory / 'experiment.json').read_text())
    seen = set()
    for item in plan['planned_runs']:
        key = (item['trial'], item['task'], item['arm'])
        if key in seen:
            raise ValueError('Repeated trial/task/arm in experiment plan')
        seen.add(key)
        contained_file(directory, str(Path(item['path']) / 'result.json'))
    report = aggregate(directory, persist=False)
    stop_path = directory / 'provider-stop.json'
    spend_path = directory / 'spend.json'
    return {'archive': str(directory), 'id': directory.name, 'verification': verification,
            'backend': plan['backend'], 'suite_sha256': plan['suite']['sha256'],
            'settings': plan['settings'], 'max_repairs': plan['max_repairs'],
            'provider_stop': json.loads(stop_path.read_text()) if stop_path.exists() else None,
            'spend': json.loads(spend_path.read_text()) if spend_path.exists() else None,
            'report': report}


def build_catalog(directories):
    paths = [Path(p).resolve() for p in directories]
    if not paths or len(set(paths)) != len(paths):
        raise ValueError('Supply distinct experiment archive directories')
    experiments, seen, accounting = [], set(), {}
    for path in sorted(paths):
        item = inspect_experiment(path)
        fingerprint = item['verification']['checksums_sha256']
        if fingerprint in seen:
            raise ValueError('Duplicate archive content; refusing double counting')
        seen.add(fingerprint)
        experiments.append(item)
        backend = item['backend']
        key = backend['backend'] + ':' + backend.get('model', backend['provenance'])
        totals = accounting.setdefault(key, {'model_calls': 0, 'input_tokens': 0,
            'output_tokens': 0, 'usage_unknown_calls': 0, 'accounted_usd': 0})
        for field, count in item['report']['usage'].items():
            totals[field] += count
        if item['spend']:
            totals['accounted_usd'] += item['spend']['accounted_usd']
    return {'schema': 1, 'experiments': experiments, 'experiment_accounting': accounting,
            'interpretation': 'Each admitted batch is separate. No pooled semantic accuracy is calculated. '
                'Different subjects, protocols, repeated candidates, and infrastructure failures are not independent samples. '
                'Accounting includes failed and integrity-invalid experiment calls; standalone diagnostics are outside this catalog. '
                'Accounted dollars are conservative reservations, not measured charges.'}


def render_catalog(catalog):
    lines = ['# Experiment history', '', catalog['interpretation'], '',
             '| Archive | Model / provenance | Study | One-shot | Code repair | Environment repair | Calls |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for item in catalog['experiments']:
        report, backend = item['report'], item['backend']
        scores = [f"{report['arms'][arm]['tasks_passing']}/{report['arms'][arm]['admitted_task_trials']}"
                  for arm in ('one_shot', 'code_repair', 'environment_repair')]
        lines.append('| ' + ' | '.join([item['id'], backend.get('model', backend['provenance']),
            report['study'], *scores, str(report['usage']['model_calls'])]) + ' |')
    lines += ['', 'Scores above are operational task/trial passes over all admitted trials. '
              'An unavailable or unrun trial earns no operational pass; it is not an observed incorrect translation.', '']
    for item in catalog['experiments']:
        report = item['report']
        lines += ['## ' + item['id'], '',
                  f"Verified {item['verification']['verified_files']} files. Provenance: `{report['provenance']}`.", '',
                  '| Task | One-shot completed / admitted | One-shot fully passing | Initials with visible failures |',
                  '| --- | ---: | ---: | ---: |']
        for task, results in report['by_task'].items():
            initial = results['arms']['one_shot']
            lines.append(f"| {task} | {initial['completed_task_trials']}/{initial['admitted_task_trials']} | "
                f"{initial['tasks_passing']} | {results['repair_opportunities']['initials_with_visible_failures']} |")
        if item['provider_stop']:
            lines += ['', 'Provider stop: `' + item['provider_stop']['reason'] + '`.']
        lines.append('')
    return '\n'.join(lines)
