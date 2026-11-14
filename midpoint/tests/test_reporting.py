import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from migration_lab.cli import main
from migration_lab.reporting import build_catalog, inspect_experiment, verify_archive, render_catalog
from migration_lab.storage import save_json, sha256


def archive(path):
    path.mkdir()
    save_json(path/'experiment.json', {
        'backend': {'backend': 'test', 'provenance': 'live_model', 'model': 'test-model'},
        'study': 'natural_translation', 'settings': {}, 'max_repairs': 5,
        'suite': {'sha256': 'test-suite', 'counts': {'normalized': {'visible': 2, 'holdout': 3}}},
        'runtimes': ['cpython', 'graal'], 'planned_runs': [
            {'trial': 0, 'task': 'normalized', 'arm': arm, 'path': arm}
            for arm in ('one_shot', 'code_repair', 'environment_repair')]})
    for arm in ('one_shot', 'code_repair', 'environment_repair'):
        save_json(path/arm/'result.json', {'status': 'not_run', 'not_run_reason': 'provider_circuit_open'})
    save_json(path/'summary.json', {'historical_schema': 'must remain byte identical'})
    save_json(path/'checksums.json', {str(p.relative_to(path)): sha256(p) for p in path.rglob('*') if p.is_file()})
    return path


class ReportingTests(unittest.TestCase):
    def test_inspection_and_cli_report_never_rewrite_archived_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = archive(Path(tmp)/'archive')
            before = {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()}
            report = inspect_experiment(path)['report']
            self.assertEqual(report['arms']['one_shot']['admitted_task_trials'], 1)
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['report', str(path)]), 0)
            self.assertEqual(json.loads(output.getvalue()), report)
            self.assertEqual(before, {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()})

    def test_modified_added_and_missing_files_are_rejected(self):
        for modification in ('modify', 'add', 'delete'):
            with self.subTest(modification=modification), tempfile.TemporaryDirectory() as tmp:
                path = archive(Path(tmp)/'archive')
                if modification == 'modify':
                    (path/'summary.json').write_text('{}')
                elif modification == 'add':
                    (path/'extra.json').write_text('{}')
                else:
                    (path/'summary.json').unlink()
                with self.assertRaises(ValueError): verify_archive(path)

    def test_manifest_cannot_escape_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = archive(root/'archive')
            (root/'outside').write_text('private')
            (path/'link').symlink_to(root/'outside')
            manifest = json.loads((path/'checksums.json').read_text())
            manifest['link'] = sha256(root/'outside')
            save_json(path/'checksums.json', manifest)
            with self.assertRaisesRegex(ValueError, 'invalid file path'): verify_archive(path)

    def test_duplicate_archives_cannot_double_count_trials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = archive(root/'archive')
            shutil.copytree(path, root/'copy')
            with self.assertRaises(ValueError): build_catalog([path, path])
            with self.assertRaisesRegex(ValueError, 'Duplicate archive content'): build_catalog([path, root/'copy'])

    def test_catalog_retains_failures_and_refuses_output_inside_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = archive(root/'archive')
            catalog = build_catalog([path])
            self.assertEqual(catalog['experiments'][0]['report']['arms']['one_shot']['completed_task_trials'], 0)
            self.assertIn('0/1', render_catalog(catalog))
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['catalog', str(path), '--output', str(path/'report.md')])
            self.assertFalse((path/'report.md').exists())
            output = root/'report.md'
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main(['catalog', str(path), '--output', str(output)]), 0)
                original = output.read_bytes()
                self.assertEqual(main(['catalog', str(path), '--output', str(output)]), 2)
                self.assertEqual(output.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
