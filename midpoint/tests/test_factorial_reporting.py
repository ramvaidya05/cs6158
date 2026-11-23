import unittest
from migration_lab.factorial_reporting import summarize, ARMS

class FactorialReportingTests(unittest.TestCase):
    def test_incomplete_pair_not_counted_as_failure(self):
        result=summarize({'status':'failed','trials':[{'trial':0,'arms':{}}]})
        self.assertEqual(result['completed_pairs'],0)
        self.assertEqual(result['incomplete_pairs'],1)
        self.assertEqual(result['arms']['both']['completed_trials'],0)

    def test_interaction_uses_paired_outcomes(self):
        arms={a:{'full_pass': a=='both', 'holdout':{m:{'passed':1,'total':1} for m in ('cpython','graal')}} for a in ARMS}
        report=summarize({'status':'completed','trials':[{'trial':0,'arms':arms}]})
        self.assertEqual(report['contrasts'][0]['interaction'],1)
        self.assertEqual(report['arms']['both']['full_passes'],1)
