import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from migration_lab.csv_context import compact_java
from migration_lab.csv_v2_cases import cases
from migration_lab.csv_cases import cases as v1
from migration_lab.csv_task import prompt, contract
from migration_lab.protocol import freeze, FrozenSuite
from migration_lab.storage import ROOT


def signature(row):
    return json.dumps({k:v for k,v in row.items() if k!='id'},sort_keys=True)


class CsvV2Tests(unittest.TestCase):
    def test_old_holdout_is_development_and_new_holdout_disjoint(self):
        dev={signature(r) for r in cases()}
        old={signature(r) for r in v1()+v1('holdout')}
        held={signature(r) for r in cases('holdout')}
        self.assertTrue(old <= dev)
        self.assertFalse(dev & held)
        self.assertEqual(len(held),59)
        self.assertEqual(len(dev),101)
    def test_compactor_preserves_literal_comment_markers_and_token_boundaries(self):
        source = 'String s="http://x/*keep*/"; char c=\'/\'; int/*drop*/x; //gone\nString t="a\\\"//b";'
        result=compact_java(source)
        self.assertIn('"http://x/*keep*/"',result)
        self.assertIn('"a\\\"//b"',result)
        self.assertIn('int x',result)
        self.assertNotIn('drop',result)
        self.assertNotIn('gone',result)
    def test_prompt_reduction_and_no_test_ids(self):
        text=prompt()
        raw=sum(len((ROOT/p).read_text().encode()) for p in contract()['source_files'])
        self.assertLess(len(text.encode()),raw*.5)
        self.assertIn('int readEscape()',text)
        self.assertIn('UTF-16',text)
        self.assertFalse(any(r['id'] in text for r in cases()+cases('holdout')))
    def test_freeze_v2_and_fail_closed_when_profile_changes(self):
        def reference(_, rows, directory):
            return [{'id':r['id'],'status':'ok','value':[] if r['operation']=='parse' else ''} for r in rows]
        with tempfile.TemporaryDirectory() as tmp, patch('migration_lab.protocol.TestsuiteAgent.reference',reference):
            path=Path(tmp)/'suite.json'
            suite=freeze(path,6158,tasks=('commons_csv',),profile='commons-csv-v2')
            self.assertEqual(suite.identity()['counts']['commons_csv'],{'visible':101,'holdout':59})
            payload=json.loads(path.read_text());payload['profile_sha256']='changed';path.write_text(json.dumps(payload))
            with self.assertRaises(RuntimeError):FrozenSuite(path)
