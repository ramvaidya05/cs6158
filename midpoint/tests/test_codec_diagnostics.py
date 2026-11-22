import json
from pathlib import Path
import unittest

from scripts.codec_hex_pilot import equivalent_observation


class CodecDiagnosticsTests(unittest.TestCase):
    def test_runtime_error_retains_candidate_location(self):
        source = "def run(operation, data, lower=True):\n    raise AttributeError('missing digit API')\n"
        scope = {"_source": source, "_cases_json": json.dumps([
            {"id": "probe", "task": "commons_codec_hex", "operation": "decode", "data": "00"}]),
            "_contract_json": "{}"}
        driver = Path(__file__).resolve().parents[1] / "migration_lab/guest_driver.py"
        exec(compile(driver.read_text(), str(driver), "exec"), scope)
        row = json.loads(scope["_result_json"])[0]
        self.assertEqual(row["type"], "AttributeError")
        self.assertIn("missing digit API", row["diagnostic"]["message"])
        self.assertIn('candidate.py', row["diagnostic"]["traceback"])
        self.assertFalse(equivalent_observation(
            {"id": "probe", "status": "ok", "value": [0]}, row))

    def test_diagnostics_do_not_affect_exception_scoring(self):
        expected = {"id": "probe", "status": "exception", "type": "DecoderException"}
        self.assertTrue(equivalent_observation(expected, {**expected, "diagnostic": {"message": "detail"}}))
        self.assertFalse(equivalent_observation(expected, {**expected, "type": "AttributeError"}))
