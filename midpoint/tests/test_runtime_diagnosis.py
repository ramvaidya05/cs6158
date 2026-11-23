import unittest
from migration_lab.runtime_diagnosis import decimal_bases
from scripts.validator_runtime_repair import accepts, repair_prompt

class RuntimeDiagnosisTests(unittest.TestCase):
    def test_rejects_incomplete_or_irregular_java_mapping(self):
        with self.assertRaises(ValueError): decimal_bases('A')
        values = ['A'] * 65536
        for n in range(10): values[48+n] = chr(66+n)
        self.assertEqual(decimal_bases(''.join(values)), [48])
        values[57] = 'A'
        with self.assertRaises(ValueError): decimal_bases(''.join(values))

    def test_rejects_cross_runtime_regression(self):
        def result(a, b):
            return {m: {'status': 'completed', 'passed_ids': ids} for m, ids in [('cpython', a), ('graal', b)]}
        base = result(['a'], ['a'])
        self.assertFalse(accepts(base, result(['a','b'], ['b'])))
        self.assertFalse(accepts(base, base))
        self.assertTrue(accepts(base, result(['a','b'], ['a','b'])))

    def test_prompt_uses_only_supplied_visible_feedback(self):
        visible = {m: {'failures': []} for m in ('cpython','graal')}
        question = repair_prompt('def run(a,b): pass', visible, {'runtimes': {}})
        self.assertNotIn('validator-holdout', question)
        self.assertIn('Trusted environment diagnosis', question)

    def test_portability_fix_is_bounded(self):
        from scripts.validator_portability_fix import remediate
        diagnosis = {'runtimes': {'graal': {'decimal': {'callable': False}}},
                     'java_char_values_verified': 65536, 'java_decimal_bases': [48, 1632]}
        source = 'import unicodedata\ndef run(c): return unicodedata.decimal(c)'
        scope = {}
        exec(remediate(source, diagnosis), scope)
        self.assertEqual(scope['run']('٣'), 3)
        with self.assertRaises(ValueError): scope['run']('²')
        with self.assertRaises(ValueError): remediate('def run(c): return 0', diagnosis)
        with self.assertRaises(ValueError): remediate(source.replace('decimal(c)', 'decimal(c, 0)'), diagnosis)
