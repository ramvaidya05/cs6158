import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from migration_lab.backends import BackendError, GeminiBackend
from migration_lab.budget import SpendBudget


def reply(text, finish='STOP', thought=None, version='gemini-test-001'):
    parts = ([{'text': thought, 'thought': True}] if thought else []) + [{'text': text}]
    return {'candidates': [{'content': {'parts': parts}, 'finishReason': finish}], 'modelVersion': version,
            'responseId': 'r1', 'usageMetadata': {'promptTokenCount': 10, 'candidatesTokenCount': 5,
                                                   'thoughtsTokenCount': 20}}


class GeminiAdapter(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, GEMINI_API_KEY='secret-sentinel')
        env.start()
        self.addCleanup(env.stop)

    def call(self, raw, backend=None):
        backend = backend or GeminiBackend('test')
        with patch.dict(os.environ, GEMINI_API_KEY='secret-sentinel'), \
                patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(raw).encode())):
            return backend.generate('x', 0, 'prompt')

    def test_success_skips_thoughts_and_counts_thinking_as_output(self):
        budget = SpendBudget(1, 1, 1)
        result = self.call(reply('{"code":"x = 1","explanation":"e"}', thought='hidden'), GeminiBackend('test', budget=budget))
        self.assertEqual(result['code'], 'x = 1')
        self.assertEqual(result['metadata']['usage']['output_tokens'], 25)
        self.assertTrue(budget.entries[0]['usage_known'])

    def test_failure_kinds(self):
        for raw, kind in ((reply('{}', finish='MAX_TOKENS'), 'incomplete'), (reply('{}', finish='SAFETY'), 'refusal'),
                          ({'promptFeedback': {'blockReason': 'OTHER'}}, 'refusal'),
                          (reply('{"code":"x"}'), 'malformed_output'), ({'candidates': []}, 'malformed_output')):
            with self.subTest(kind=kind), self.assertRaises(BackendError) as cm:
                self.call(raw)
            self.assertEqual(cm.exception.kind, kind)

    def test_http_errors_are_classified_and_key_redacted(self):
        body = json.dumps({'error': {'status': 'RESOURCE_EXHAUSTED', 'message': 'quota exceeded secret-sentinel'}}).encode()
        for code, kind in ((401, 'authentication'), (403, 'access_denied'), (429, 'quota'), (500, 'http_error')):
            with self.subTest(code=code), patch.dict(os.environ, GEMINI_API_KEY='secret-sentinel'), \
                    patch('urllib.request.urlopen', side_effect=HTTPError('u', code, 'm', {}, io.BytesIO(body))):
                with self.assertRaises(BackendError) as cm:
                    GeminiBackend('test').generate('x', 0, 'prompt')
                self.assertEqual(cm.exception.kind, kind)
                self.assertNotIn('secret-sentinel', str(cm.exception) + str(cm.exception.details))

    def test_model_change_is_rejected(self):
        backend = GeminiBackend('test')
        self.call(reply('{"code":"x","explanation":""}'), backend)
        with self.assertRaises(BackendError) as cm:
            self.call(reply('{"code":"x","explanation":""}', version='other'), backend)
        self.assertEqual(cm.exception.kind, 'model_changed')


if __name__ == '__main__':
    unittest.main()
