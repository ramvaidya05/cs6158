"""Contract and evaluation failure tests; no model calls or untrusted code."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from migration_lab import cli_task
from migration_lab.scenarios import validate_cases, validate_rows, strict_equal, first_difference, validate_implementation, execute_scenario
from migration_lab.evaluation import equivalent
from migration_lab.environment import EnvironmentAgent
from migration_lab.protocol import FrozenSuite, freeze
from migration_lab.storage import ROOT, sha256
from migration_lab.benchmark import verify_vendor
from migration_lab.translator import MigrationAgent


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.contract = cli_task.contract()
        self.rows = cli_task.cases()

    def invalid(self, operation):
        rows = copy.deepcopy(self.rows[:1]); rows[0]['operations'] = [operation]
        with self.assertRaises(ValueError): validate_cases(rows, self.contract)

    def test_source_pin_and_identity(self):
        self.assertTrue(cli_task.verify_source())
        self.assertIn('migration_lab/guest_driver.py', cli_task.identity())

    def test_deterministic_disjoint_cases(self):
        holdout = cli_task.cases('holdout', 42)
        self.assertEqual(holdout, cli_task.cases('holdout', 42))
        self.assertNotEqual(holdout, cli_task.cases('holdout', 43))
        visible = {json.dumps(c['operations'], sort_keys=True) for c in self.rows}
        self.assertTrue(all(json.dumps(c['operations'], sort_keys=True) not in visible for c in holdout))
        self.assertEqual((len(self.rows), len(holdout)), (20, 60))

    def test_reject_unknown_constructor(self): self.invalid(cli_task.new('File', 'file', '/tmp/x'))
    def test_reject_bad_constructor_type(self): self.invalid(cli_task.new([], 'file'))
    def test_reject_unknown_receiver(self): self.invalid(cli_task.call('missing', 'getArgs'))
    def test_reject_int_boolean(self): self.invalid(cli_task.new('DefaultParser', 'parser', 1))
    def test_reject_extra_operation_fields(self):
        op = cli_task.new('Options', 'opts'); op['path'] = '/tmp/x'; self.invalid(op)
    def test_reject_duplicate_handles(self):
        rows = copy.deepcopy(self.rows[:1]); rows[0]['operations'][1]['save'] = 'flag'
        with self.assertRaises(ValueError): validate_cases(rows, self.contract)
    def test_reject_wrong_reference_type(self):
        rows = copy.deepcopy(self.rows[:1]); rows[0]['operations'][3]['args'] = [{'ref':'options'}]
        with self.assertRaises(ValueError): validate_cases(rows, self.contract)
    def test_reject_duplicate_ids(self):
        with self.assertRaises(ValueError): validate_cases(self.rows[:1] * 2, self.contract)
    def test_reject_unbound_parse_result(self):
        rows = copy.deepcopy(self.rows[1:2]); del rows[0]['operations'][6]['save']
        with self.assertRaises(ValueError): validate_cases(rows, self.contract)
    def test_exact_comparison(self):
        self.assertFalse(strict_equal({'value':True}, {'value':1}))
        expected = {'status':'ok','trace':[{'step':0,'status':'ok','value':['a','b']}]}
        actual = copy.deepcopy(expected); actual['trace'][0]['value'].reverse()
        self.assertFalse(equivalent(expected, actual))
        self.assertEqual(first_difference(expected, actual)['step'], 0)
    def test_missing_classes_rejected(self):
        with self.assertRaises(TypeError): validate_implementation({}, self.contract)
    def test_trace_validation(self):
        row = {'status':'ok','trace':[{'step':0,'status':'ok','value':None}]}
        with self.assertRaises(ValueError): validate_rows([row], self.rows[:1])
        row['trace'][0] = {'step':0,'status':'exception','type':'ValueError'}
        validate_rows([row], self.rows[:1])
        row['trace'].append({'step':1,'status':'ok','value':None})
        with self.assertRaises(ValueError): validate_rows([row], self.rows[:1])
    def test_prompt_has_source_not_evaluator_or_fixture(self):
        prompt = MigrationAgent(None).prompt('commons_cli')
        self.assertIn('class DefaultParser', prompt)
        self.assertNotIn('commons_cli-visible-', prompt)
        self.assertNotIn('def execute_scenario', prompt)
        self.assertNotIn('Hand-written qualification fixture', prompt)
    def test_missing_api_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); candidate=path/'candidate.py'; candidate.write_text('def run(*args): return 0')
            result=EnvironmentAgent().run('cpython', self.rows[:1], path/'result', candidate)
            self.assertEqual(result['status'], 'syntax_error')
    def test_alias_and_state_bug_are_observable(self):
        good={}; bad={}
        exec((ROOT/'fixtures/commons_cli.py').read_text(), good)
        exec((ROOT/'fixtures/commons_cli_broken.py').read_text(), bad)
        case=next(c for c in self.rows if c['id'].endswith('reuse-parser'))
        expected=execute_scenario(good,case,self.contract); actual=execute_scenario(bad,case,self.contract)
        self.assertEqual(first_difference(expected, actual)['step'], 7)
        alias=execute_scenario(good,self.rows[0],self.contract)
        self.assertEqual(alias['trace'][3]['value'], {'ref':'options'})
    def test_observations_are_snapshots(self):
        scope = {}
        exec((ROOT/'fixtures/commons_cli.py').read_text(), scope)
        scope['Options'].getRequiredOptions = lambda self: self.required
        case = {'id':'snapshots','task':'commons_cli','operations':[
            cli_task.new('Options','options'), cli_task.call('options','getRequiredOptions'),
            cli_task.new('Option','option','x','example',False,'description'),
            cli_task.call('option','setRequired',True),
            cli_task.call('options','addOption',cli_task.ref('option')),
            cli_task.call('options','getRequiredOptions')]}
        result=execute_scenario(scope,case,self.contract)
        self.assertEqual(result['trace'][1]['value'], [])
        self.assertEqual(result['trace'][5]['value'], ['x'])

    def test_frozen_suite_binds_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'suite.json'
            def reference(_, rows, directory):
                return [{'id':r['id'],'status':'ok','trace':[{'step':0,'status':'exception','type':'Fixture'}]} for r in rows]
            with patch('migration_lab.protocol.TestsuiteAgent.reference', reference):
                suite=freeze(path,42,tasks=('commons_cli',))
            self.assertEqual(suite.identity()['counts']['commons_cli']['holdout'],60)
            with patch('migration_lab.cli_task.identity', return_value={}):
                with self.assertRaises(RuntimeError): FrozenSuite(path)

if __name__ == '__main__': unittest.main()
