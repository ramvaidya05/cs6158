import json
import unittest
from migration_lab.storage import ROOT
from scripts.validator_luhn_pilot import cases, prompt, verify_source

class ValidatorPilotTests(unittest.TestCase):
    def evaluate(self, source, operation):
        scope = {'_source': source, '_cases_json': json.dumps([{'id': 'x', 'task': 'commons_validator_luhn', 'operation': operation, 'data': None}]), '_contract_json': '{}'}
        exec((ROOT / 'migration_lab/guest_driver.py').read_text(), scope)
        return json.loads(scope['_result_json'])[0]

    def test_boolean_contract_rejects_integer(self):
        row = self.evaluate('def run(operation, data): return 1', 'isValid')
        self.assertEqual(row['type'], 'TypeError')

    def test_exception_normalization(self):
        row = self.evaluate('def run(operation, data): raise ValueError()', 'calculate')
        self.assertEqual(row, {'id': 'x', 'status': 'exception', 'type': 'CheckDigitException'})

    def test_null_preserved(self):
        row = self.evaluate('def run(operation, data): return data is None', 'isValid')
        self.assertIs(row['value'], True)

    def test_frozen_cases_and_prompt_separation(self):
        suite = cases()
        self.assertEqual(suite, cases())
        self.assertEqual(len(suite['visible']), 30)
        self.assertEqual(len(suite['holdout']), 130)
        self.assertNotIn('9' * 1000, prompt())
        self.assertNotIn('validator-holdout', prompt())
        self.assertEqual(verify_source()['version'], '1.9.0')
