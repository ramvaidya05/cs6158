import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from migration_lab.retry_memory import RetryMemory, diagnostics
from migration_lab.dependencies import inspect_dependencies, write_requirements
from migration_lab.controller import run_task
from migration_lab.cli_extended import cases
from migration_lab.cli_task import contract
from migration_lab.scenarios import validate_cases, validate_implementation
from migration_lab.storage import ROOT
from migration_lab.environment import EnvironmentAgent
from test_core import FakeBackend, FakeEnvironment, FakeTestsuite


def failed():
    row = {'passed':0, 'total':1, 'status':'completed','passed_ids':[], 'failures':[
        {'case':{'id':'visible-sentinel','operations':[{'op':'call','on':'x','method':'getValue','args':[]}]},
         'first_difference':{'step':0,'expected':{'value':None},'actual':{'value':''}}}]}
    return {'passed':0,'total':2,'all_pass':False,'runtimes':{'cpython':row,'graal':row}}


class MemoryTests(unittest.TestCase):
    def test_pruning_groups_equivalent_runtime_failures(self):
        result = diagnostics(failed())
        self.assertEqual(result['groups_total'],1)
        self.assertEqual(result['failures'][0]['occurrences'],2)
        self.assertEqual(result['failures'][0]['runtimes'],['cpython','graal'])

    def test_long_trace_bounded_and_candidate_location_preserved(self):
        summary=failed()
        summary['runtimes']['cpython']['failures']=[{'kind':'execution_error','stderr':'File "candidate.py", line 8\n'+('noise\n'*3000)+'ValueError: wrong'}]
        result=diagnostics(summary)['failures'][0]
        self.assertIn('candidate.py',result['traceback'])
        self.assertIn('ValueError',result['traceback'])
        self.assertLess(len(result['traceback']),1700)

    def test_memory_local_rejections_persist_and_no_inferred_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); memory=RetryMemory(root)
            memory.update(0,'hash-a',failed(),True)
            memory.update(1,'hash-b',failed(),False)
            self.assertIn('hash-b',memory.context())
            self.assertFalse(json.loads((root/'translation_failures.json').read_text())['attempts'][1]['accepted_checkpoint'])
            self.assertIn('causal explanation not established',memory.render())
            self.assertNotIn('hash-a',RetryMemory(root/'another-arm').context())
            self.assertLess(len(memory.context(100)),200)

    def test_controller_history_on_retry_not_initial_and_holdout_excluded(self):
        with tempfile.TemporaryDirectory() as tmp, patch('migration_lab.controller.EnvironmentAgent',FakeEnvironment), patch('migration_lab.controller.TestsuiteAgent',FakeTestsuite):
            backend=FakeBackend([[],['a'],['a','b']])
            root,state=run_task('levenshtein',backend,modes=('cpython',),directory=Path(tmp),retry_memory=True,feedback_mode='pruned')
            self.assertNotIn('VISIBLE RETRY HISTORY',backend.prompts[0])
            self.assertIn('VISIBLE RETRY HISTORY',backend.prompts[1])
            self.assertIn('"attempt": 0',backend.prompts[2])
            self.assertIn('"attempt": 1',backend.prompts[2])
            self.assertNotIn('holdout-',(root/'TRANSLATION_FAILURES.md').read_text())
            self.assertEqual(state['stop_reason'],'visible_pass')
            self.assertTrue((root/'requirements.txt').exists())

    def test_recovery_observation_and_revision_are_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=RetryMemory(Path(tmp)); memory.update(0,'old',failed(),True)
            passing=failed();passing.update(passed=2,all_pass=True)
            for row in passing['runtimes'].values():
                row.update(passed=1,passed_ids=['visible-sentinel'],failures=[])
            memory.update(1,'new',passing,True,'return ""','return None')
            self.assertEqual(len(memory.history[-1]['previously_failing_observations_now_passing']),2)
            self.assertIn('+return None',memory.history[-1]['attempted_revision_excerpt'])

    def test_memory_off_has_no_document(self):
        with tempfile.TemporaryDirectory() as tmp, patch('migration_lab.controller.EnvironmentAgent',FakeEnvironment), patch('migration_lab.controller.TestsuiteAgent',FakeTestsuite):
            root,_=run_task('levenshtein',FakeBackend([['a','b']]),modes=('cpython',),directory=Path(tmp))
            self.assertFalse((root/'TRANSLATION_FAILURES.md').exists())


class DependencyTests(unittest.TestCase):
    def test_stdlib_empty_requirements(self):
        self.assertEqual(inspect_dependencies('import json\nfrom collections import deque')['status'],'approved')
    def test_unknown_distribution_not_guessed(self):
        report=inspect_dependencies('from PIL import Image\nimport requests')
        self.assertEqual(report['unresolved_imports'],['PIL','requests'])
        self.assertEqual(report['requirements'],[])
        self.assertEqual(report['status'],'blocked')
    def test_relative_and_dynamic_imports_blocked(self):
        for source in ['from . import helper', '__import__("requests")', 'import importlib\nimportlib.import_module("requests")']:
            self.assertEqual(inspect_dependencies(source)['status'],'blocked')
    def test_syntax_error_is_not_dependency_failure(self):
        self.assertEqual(inspect_dependencies('def broken(')['status'],'syntax_error')
    def test_environment_blocks_unapproved_import_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp, patch('migration_lab.environment.execute') as execute:
            root=Path(tmp);candidate=root/'candidate.py';candidate.write_text('import unapproved_package\ndef run(*args): return 0')
            report=EnvironmentAgent().run('cpython',[{'id':'visible','task':'levenshtein'}],root/'result',candidate)
            self.assertEqual(report['status'],'dependency_policy')
            execute.assert_not_called()

    def test_proposal_archived_without_executing_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); candidate=root/'candidate.py'; candidate.write_text('raise RuntimeError("never execute")\nimport unknown_package')
            self.assertEqual(write_requirements(candidate,root)['status'],'blocked')
            self.assertNotIn('unknown_package',(root/'requirements.txt').read_text())


class ExpandedProfileTests(unittest.TestCase):
    def test_default_cli_replay_implements_extended_contract(self):
        replay=json.loads((ROOT/'fixtures/replay.json').read_text())
        for name in replay['tasks']['commons_cli']:
            scope={}
            exec((ROOT/'fixtures'/name).read_text(),scope)
            validate_implementation(scope,contract())

    def test_contract_scope_and_disjoint_sequences(self):
        spec=contract()
        self.assertEqual(sum(len(c['methods']) for c in spec['classes'].values()),32)
        visible,held=cases('visible'),cases('holdout')
        self.assertEqual((len(visible),len(held)),(44,28))
        validate_cases(visible,spec); validate_cases(held,spec)
        visible_ops={json.dumps(c['operations'],sort_keys=True) for c in visible}
        self.assertTrue(all(json.dumps(c['operations'],sort_keys=True) not in visible_ops for c in held))
