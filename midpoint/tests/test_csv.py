import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from migration_lab.csv_task import contract,identity,prompt,validate_cases,validate_rows
from migration_lab.csv_cases import cases
from migration_lab.evaluation import equivalent
from migration_lab.protocol import freeze,FrozenSuite
from migration_lab.storage import ROOT


def guest(source,rows):
    scope={'_source':source,'_cases_json':json.dumps(rows),'_contract_json':'{}'}
    exec((ROOT/'migration_lab/guest_driver.py').read_text(),scope)
    return json.loads(scope['_result_json'])


class CsvTests(unittest.TestCase):
    def test_scope_and_disjoint_compositions(self):
        visible,held=cases(),cases('holdout')
        self.assertEqual((len(visible),len(held)),(37,28))
        sig=lambda c:json.dumps({k:v for k,v in c.items() if k!='id'},sort_keys=True)
        self.assertFalse({sig(c) for c in visible}&{sig(c) for c in held})
        self.assertEqual(cases('holdout',1),cases('holdout',2))
    def test_envelope_rejects_mixed_tasks_duplicates_and_unbounded_input(self):
        for rows in [cases()[:1]*2,[{**cases()[0],'task':'levenshtein'}],[{**cases()[0],'text':'a'*16001}],
                     [{**cases()[0],'config':{'unknown':1}}]]:
            with self.assertRaises(ValueError):validate_cases(rows)
    def test_invalid_config_scalars_are_evaluated_not_silently_coerced(self):
        validate_cases([{**cases()[0],'config':{'trim':1,'delimiter':'🚀'}}])
    def test_prompt_contains_source_contract_but_no_scenarios(self):
        text=prompt()
        self.assertIn('class CSVParser',text)
        self.assertIn('parse_csv(text, config)',text)
        self.assertFalse(any(c['id'] in text for c in cases()+cases('holdout')))
        self.assertNotIn('def validate_cases',text)
    def test_comparator_preserves_types_nulls_order_and_line_endings(self):
        expected={'status':'ok','value':[['',None,'x']]}
        self.assertTrue(equivalent(expected,copy.deepcopy(expected),'commons_csv'))
        for value in [[['', '', 'x']], [['x',None,'']], [[False,None,'x']], [['',None,'X']]]:
            self.assertFalse(equivalent(expected,{'status':'ok','value':value},'commons_csv'))
        self.assertFalse(equivalent({'status':'ok','value':'x\r\n'},{'status':'ok','value':'x\n'},'commons_csv'))
    def test_exception_categories_exact(self):
        expected={'status':'exception','type':'CSVParseError'}
        self.assertTrue(equivalent(expected,dict(expected),'commons_csv'))
        self.assertFalse(equivalent(expected,{'status':'exception','type':'ValueError'},'commons_csv'))
    def test_guest_typed_results_and_exception_names(self):
        source='class CSVParseError(Exception): pass\ndef parse_csv(text, config): raise CSVParseError()\ndef print_csv(records, config): return 3'
        rows=guest(source,[cases()[0],next(c for c in cases() if c['operation']=='print')])
        self.assertEqual([r['type'] for r in rows],['CSVParseError','TypeError'])
        source='def parse_csv(text, config): return [[False]]\ndef print_csv(records, config): return ""'
        self.assertEqual(guest(source,cases()[:1])[0]['type'],'TypeError')
    def test_default_demo_routes_csv(self):
        from migration_lab.backends import ReplayBackend
        response=ReplayBackend(ROOT/"fixtures/replay.json").generate("commons_csv",0,"ignored")
        self.assertEqual(guest(response["code"],cases()[:1])[0]["status"],"ok")

    def test_missing_entrypoint_rejected(self):
        with self.assertRaises(TypeError):guest('def parse_csv(text,config): return []',cases()[:1])
    def test_rows_reject_missing_value_and_wrong_shape(self):
        case=cases()[0]
        for row in [{'id':case['id'],'status':'ok'}, {'id':case['id'],'status':'ok','value':[1]},
                    {'id':'other','status':'ok','value':[]}, {'id':case['id'],'status':'exception','type':3}]:
            with self.assertRaises(ValueError):validate_rows([row],[case])
    def test_frozen_csv_binds_identity_and_refuses_overwrite(self):
        def reference(_,rows,directory):
            return [{'id':r['id'],'status':'ok','value':[] if r['operation']=='parse' else ''} for r in rows]
        with tempfile.TemporaryDirectory() as tmp,patch('migration_lab.protocol.TestsuiteAgent.reference',reference):
            path=Path(tmp)/'suite.json'
            suite=freeze(path,6158,tasks=('commons_csv',),profile='commons-csv-v1')
            self.assertEqual(suite.identity()['counts']['commons_csv']['holdout'],28)
            with self.assertRaises(ValueError):freeze(path,6158,tasks=('commons_csv',),profile='commons-csv-v1')
            with patch('migration_lab.csv_task.identity',return_value={}):
                with self.assertRaises(RuntimeError):FrozenSuite(path)
    def test_csv_cannot_use_numeric_pilot_profile(self):
        with self.assertRaises(ValueError):freeze(Path('/unused'),tasks=('commons_csv',))
