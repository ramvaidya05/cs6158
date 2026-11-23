import unittest
from scripts.validator_factorial_study import ARMS, fresh_cases, treatment_prompt
from scripts.validator_paired_study import fresh_cases as previous_cases

class FactorialStudyTests(unittest.TestCase):
    def test_factors_are_separate(self):
        visible={m:{'failures':[]} for m in ('cpython','graal')}
        diagnosis={'runtimes':{'probe_marker': True},'java_decimal_bases':[123456]}
        for arm in ARMS:
            question=treatment_prompt('def run(a,b): pass',visible,diagnosis,arm)
            self.assertEqual('probe_marker' in question,arm in ('diagnosis_only','both'))
            self.assertEqual('123456' in question,arm in ('semantics_only','both'))

    def test_new_cases_and_balanced_order(self):
        new=fresh_cases()
        old={c['data'] for split in previous_cases().values() for c in split}
        self.assertEqual(len(new['holdout']),136)
        self.assertFalse({c['data'] for c in new['holdout']} & old)
        self.assertEqual(new,fresh_cases())
        orders=[ARMS[i:]+ARMS[:i] for i in range(4)]
        for position in range(4):
            self.assertEqual({order[position] for order in orders},set(ARMS))
