import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from migration_lab.cli_semantic import cases
from migration_lab.cli_task import contract
from migration_lab.scenarios import validate_cases
from migration_lab.translator import MigrationAgent
from migration_lab.protocol import freeze,FrozenSuite
from migration_lab.storage import ROOT

class SemanticTests(unittest.TestCase):
    def test_splits_are_valid_and_distinct_sequences(self):
        visible,held=cases('visible'),cases('holdout')
        self.assertEqual((len(visible),len(held)),(36,20))
        validate_cases(visible,contract());validate_cases(held,contract())
        serialized={json.dumps(c['operations'],sort_keys=True) for c in visible}
        self.assertTrue(all(json.dumps(c['operations'],sort_keys=True) not in serialized for c in held))
        self.assertEqual(held,cases('holdout',999))

    def test_profile_is_not_in_prompt(self):
        prompt=MigrationAgent(None).prompt('commons_cli')
        self.assertNotIn('semantic-v2-holdout',prompt)
        self.assertNotIn('three-parses-two-configurations',prompt)

    def test_feedback_is_bounded_and_does_not_leak_later_operations(self):
        failure={'case':{'id':'visible-case','operations':[{'op':'first'},{'op':'bad'},{'op':'later-secret'}]},'expected':{'trace':['full-secret']},'actual':{'trace':['full-actual']},'first_difference':{'step':1,'expected':{'value':None},'actual':{'value':''}}}
        summary={'runtimes':{'cpython':{'passed':0,'total':1,'status':'completed','failures':[failure]}}}
        basic=MigrationAgent.feedback(summary,'basic')
        self.assertEqual(set(basic['cpython']),{'passed','total','status'})
        operation=MigrationAgent.feedback(summary,'operation')
        text=json.dumps(operation)
        self.assertNotIn('later-secret',text);self.assertNotIn('full-secret',text)
        self.assertIn('first_difference',text)
        self.assertEqual(len(operation['cpython']['failures'][0]['operations']),2)
        with self.assertRaises(ValueError):MigrationAgent.feedback(summary,'unknown')

    def test_v2_fingerprint_rejects_profile_changes(self):
        def oracle(_,rows,directory):
            return [{'id':r['id'],'status':'ok','trace':[{'step':0,'status':'exception','type':'Fixture'}]} for r in rows]
        with tempfile.TemporaryDirectory() as tmp,patch('migration_lab.protocol.TestsuiteAgent.reference',oracle):
            suite=freeze(Path(tmp)/'suite.json',6158,('commons_cli',),'commons-cli-semantic-v2')
            self.assertEqual(suite.identity()['profile'],'commons-cli-semantic-v2')
            from migration_lab.storage import sha256 as real_hash
            def altered(path):
                return 'changed' if Path(path).name=='cli_semantic.py' else real_hash(path)
            with patch('migration_lab.protocol.sha256',altered),self.assertRaises(RuntimeError):suite.identity()

    def test_ablation_aggregation_preserves_failed_trials(self):
        from migration_lab.experiments import aggregate
        from migration_lab.storage import save_json
        arms=['one_shot','basic_feedback','operation_feedback']
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            save_json(path/'experiment.json',{'backend':{'provenance':'synthetic_fixture'},'study':'feedback_ablation','arms':arms,'suite':{'counts':{'commons_cli':{'visible':36,'holdout':20}}},'runtimes':['cpython','graal'],'planned_runs':[{'trial':0,'task':'commons_cli','arm':a,'path':a} for a in arms]})
            save_json(path/'operation_feedback/result.json',{'status':'selected','attempts':[{'status':'evaluated'},{'status':'backend_error'}],'backend_failure':{'kind':'budget'}})
            result=aggregate(path)
            blocked=next(r for r in result['runs'] if r['arm']=='operation_feedback')
            self.assertEqual(blocked['code_repairs'],0)
            self.assertEqual(blocked['repair_attempts'],1)
            self.assertTrue(blocked['repair_budget_blocked'])
            self.assertEqual(set(result['arms']),set(arms))
            self.assertEqual(len(result['paired_changes']),2)
            self.assertEqual(result['arms']['basic_feedback']['runtimes']['graal']['holdout']['unvalidated'],20)

    def test_v2_requires_cli_task(self):
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):
            freeze(Path(tmp)/'suite.json',tasks=('levenshtein',),profile='commons-cli-semantic-v2')

if __name__=='__main__':unittest.main()
