import unittest
from scripts.validator_paired_study import fresh_cases, all_pass
from scripts.validator_luhn_pilot import prompt

class PairedDiagnosisTests(unittest.TestCase):
    def test_fresh_suite_is_deterministic_and_disjoint(self):
        suite=fresh_cases()
        self.assertEqual(suite,fresh_cases())
        self.assertEqual(len(suite['holdout']),136)
        visible={(c['operation'],c['data']) for c in suite['visible']}
        self.assertTrue(all((c['operation'],c['data']) not in visible for c in suite['holdout']))
        self.assertNotIn('paired-held',prompt())
        self.assertTrue(any(c['data']=='\ud800' for c in suite['holdout']))

    def test_full_success_requires_completed_both_runtimes(self):
        scores={m:{'status':'completed','passed':30,'total':30} for m in ('cpython','graal')}
        self.assertTrue(all_pass(scores))
        scores['graal']['status']='timeout'
        self.assertFalse(all_pass(scores))
