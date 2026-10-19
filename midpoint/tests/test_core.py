import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from migration_lab.backends import BackendError, ReplayBackend, OpenAIResponsesBackend, parse_response
from migration_lab.benchmark import TASKS, cases, verify_vendor
from migration_lab.controller import improves_without_regression, assert_unchanged, run_task
from migration_lab.environment import EnvironmentAgent
from migration_lab.evaluation import equivalent, TestsuiteAgent
from migration_lab.process import execute
from migration_lab.storage import ROOT, save_json
from migration_lab.translator import MigrationAgent


def summary(ids, total=2):
    return {"passed": len(ids), "total": total, "all_pass": len(ids) == total,
            "runtimes": {"cpython": {"passed_ids": ids, "passed": len(ids), "total": total,
                         "status": "completed", "failures": []}}}


class ComparatorTests(unittest.TestCase):
    def test_numeric_tolerance(self):
        self.assertTrue(equivalent({"status": "ok", "value": 0.5}, {"status": "ok", "value": 0.5 + 1e-10}))
        self.assertFalse(equivalent({"status": "ok", "value": 0.5}, {"status": "ok", "value": 0.51}))

    def test_non_numeric_never_passes(self):
        for value in (True, None, "1", float("nan"), float("inf"), 10 ** 1000):
            with self.subTest(value=value):
                self.assertFalse(equivalent({"status": "ok", "value": 1}, {"status": "ok", "value": value}))

    def test_explicit_exception_contract(self):
        expected = {"status": "exception", "type": "NullPointerException"}
        self.assertTrue(equivalent(expected, {"status": "exception", "type": "ValueError"}))
        self.assertFalse(equivalent(expected, {"status": "exception", "type": "TypeError"}))
        self.assertFalse(equivalent(expected, {"status": "ok", "value": 0}))

    def test_empty_suite_rejected(self):
        with self.assertRaises(ValueError):
            TestsuiteAgent(None).evaluate(None, [], [], ["cpython"], None)

    def test_regression_rejected_even_with_higher_score(self):
        self.assertFalse(improves_without_regression(summary(["b", "c"]), summary(["a"])))
        self.assertTrue(improves_without_regression(summary(["a", "b"]), summary(["a"])))
        self.assertFalse(improves_without_regression(summary(["a"]), summary(["a"])))

    def test_source_guard_detects_mutation(self):
        with patch("migration_lab.controller.protected_hashes", return_value={"x": "new"}):
            with self.assertRaisesRegex(RuntimeError, "invalidated"):
                assert_unchanged({"x": "original"})


class BenchmarkTests(unittest.TestCase):
    def test_pinned_source_checksums(self):
        self.assertEqual(verify_vendor()["commit"], "93240df9aab3ecea98b869c9536aa7ebc555b281")

    def test_case_counts_ids_and_determinism(self):
        for task in TASKS:
            visible, held = cases(task), cases(task, "holdout")
            self.assertEqual((len(visible), len(held)), (26, 20))
            self.assertEqual(held, cases(task, "holdout"))
            self.assertFalse(set(c["id"] for c in visible) & set(c["id"] for c in held))
            self.assertNotEqual(held, cases(task, "holdout", 123))

    def test_invalid_task_rejected(self):
        with self.assertRaises(ValueError):
            cases("invented")

    def test_prompt_contains_source_but_not_holdout(self):
        prompt = MigrationAgent(None).prompt("levenshtein")
        self.assertIn("class Levenshtein", prompt)
        self.assertIn("UTF-16", prompt)
        self.assertNotIn("withheld", prompt)
        self.assertNotIn("holdout-", prompt)
        self.assertNotIn("fixtures/", prompt)


class BackendTests(unittest.TestCase):
    def test_replay_is_explicitly_synthetic(self):
        backend = ReplayBackend(ROOT / "fixtures/replay.json")
        response = backend.generate("levenshtein", 0, "ignored")
        self.assertEqual(response["metadata"]["provenance"], "synthetic_fixture")
        self.assertIsNone(response["metadata"]["usage"])

    def test_replay_exhaustion(self):
        with self.assertRaises(BackendError):
            ReplayBackend(ROOT / "fixtures/replay.json").generate("levenshtein", 10, "")

    def test_replay_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / "replay.json"
            save_json(p, {"provenance": "synthetic_fixture", "tasks": {"x": ["../secret"]}})
            with self.assertRaisesRegex(BackendError, "escapes"):
                ReplayBackend(p).generate("x", 0, "")

    def test_structured_response_parsing(self):
        raw = {"status": "completed", "output": [{"type": "reasoning"},
               {"type": "message", "content": [{"type": "output_text",
                "text": json.dumps({"code": "def run(a,b): return 0", "explanation": "ok"})}]}]}
        self.assertIn("def run", parse_response(raw)["code"])

    def test_incomplete_refused_and_malformed_rejected(self):
        for raw in ({"status": "incomplete"}, {"status": "completed", "output": []},
                    {"status": "completed", "output": [{"type": "message", "content": [
                        {"type": "refusal", "refusal": "no"}]}]}):
            with self.subTest(raw=raw), self.assertRaises(BackendError):
                parse_response(raw)

    def test_live_adapter_request_and_usage_with_mock_transport(self):
        raw = {"status": "completed", "model": "test-model", "id": "test-id",
               "usage": {"input_tokens": 12, "output_tokens": 9},
               "output": [{"type": "message", "content": [{"type": "output_text",
                           "text": json.dumps({"code": "def run(*args): return 0", "explanation": "test"})}]}]}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-sentinel"}), \
                patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(raw).encode())) as transport:
            response = OpenAIResponsesBackend("test-model").generate("levenshtein", 0, "test prompt", max_output_tokens=100)
        request = transport.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(body["input"], "test prompt")
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertFalse(body["store"])
        self.assertEqual(body["max_output_tokens"], 100)
        self.assertEqual(response["metadata"]["usage"]["output_tokens"], 9)
        self.assertNotIn("test-only-sentinel", json.dumps(response))

    def test_live_adapter_requires_explicit_model_and_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                OpenAIResponsesBackend("test-model")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-sentinel"}):
            with self.assertRaises(ValueError):
                OpenAIResponsesBackend(None)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def candidate(self, text):
        path = self.base / "candidate.py"
        path.write_text(text)
        return path

    def test_stdout_is_separate_and_results_match_ids(self):
        source = self.candidate("print('debug')\ndef run(a,b,operation,parameter): return 7\n")
        result = EnvironmentAgent().run("cpython", cases("levenshtein")[:1], self.base / "run", source)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["rows"][0]["value"], 7)
        self.assertIn("debug", result["process"]["stderr"])

    def test_syntax_failure_and_missing_entrypoint(self):
        for code in ("def broken(", "x = 5"):
            with self.subTest(code=code):
                result = EnvironmentAgent().run("cpython", cases("levenshtein")[:1], self.base / "run", self.candidate(code))
                self.assertEqual(result["status"], "syntax_error")

    def test_runtime_exception_preserved(self):
        source = self.candidate("def run(*args): raise ValueError('bad input')\n")
        result = EnvironmentAgent().run("cpython", cases("levenshtein")[:1], self.base / "run", source)
        self.assertEqual(result["rows"][0]["type"], "ValueError")

    def test_infinite_loop_times_out(self):
        source = self.candidate("def run(*args):\n    while True: pass\n")
        result = EnvironmentAgent(0.2).run("cpython", cases("levenshtein")[:1], self.base / "run", source)
        self.assertEqual(result["status"], "timeout")

    def test_credentials_not_forwarded(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-sentinel"}):
            result = execute([sys.executable, "-I", "-c",
                              "import os; print('OPENAI_API_KEY' in os.environ)"])
        self.assertEqual(result["stdout"].strip(), "False")

    def test_nonfinite_result_rejected(self):
        result = EnvironmentAgent().run("cpython", cases("levenshtein")[:1], self.base / "run",
                    self.candidate("def run(*args): return float('nan')\n"))
        self.assertEqual(result["rows"][0]["type"], "TypeError")

    def test_malformed_runner_output_rejected(self):
        source = self.candidate("def run(*args): return 0")
        for output in ("not json", "[]", '[{"id":"wrong","status":"ok","value":0}]'):
            process = {"stdout": output, "stderr": "", "exit_code": 0,
                       "timed_out": False, "output_truncated": False}
            with self.subTest(output=output), patch("migration_lab.environment.execute", return_value=process):
                result = EnvironmentAgent().run("cpython", cases("levenshtein")[:1], self.base / "run", source)
                self.assertEqual(result["status"], "protocol_error")


class FakeBackend:
    identity = {"provenance": "synthetic_fixture", "backend": "test"}

    def __init__(self, sequence):
        self.sequence, self.prompts = sequence, []

    def generate(self, task, attempt, prompt, **kwargs):
        self.prompts.append(prompt)
        return {"code": json.dumps(self.sequence[attempt]), "metadata": {}}


class FakeEnvironment:
    def __init__(self, timeout):
        pass

    def doctor(self):
        return {"test_double": True}

    def run(self, *args):
        return {"status": "completed", "rows": [{"value": 0}]}


class FakeTestsuite:
    def __init__(self, environment):
        pass

    def reference(self, cases, directory):
        return [{"id": c["id"], "status": "ok", "value": 1} for c in cases]

    def evaluate(self, candidate, cases, reference, modes, directory):
        ids = json.loads(candidate.read_text())
        return summary(ids)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, value in (("EnvironmentAgent", FakeEnvironment), ("TestsuiteAgent", FakeTestsuite)):
            patcher = patch("migration_lab.controller." + target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_sequence(self, sequence, **kwargs):
        backend = FakeBackend(sequence)
        path, state = run_task("levenshtein", backend, modes=("cpython",), directory=Path(self.tmp.name), **kwargs)
        self.assertTrue((path / "selection.json").exists())
        return backend, state

    def test_success_and_holdout_not_in_prompts(self):
        backend, state = self.run_sequence([[], ["a", "b"]])
        self.assertEqual(state["best_attempt"], 1)
        self.assertEqual(state["stop_reason"], "visible_pass")
        self.assertEqual(len(backend.prompts), 2)
        self.assertTrue(all("holdout-" not in p for p in backend.prompts))

    def test_zero_repairs_is_one_shot(self):
        backend, state = self.run_sequence([["a"]], max_repairs=0)
        self.assertEqual(len(backend.prompts), 1)
        self.assertEqual(state["stop_reason"], "attempt_limit")

    def test_repeated_candidate_stops(self):
        _, state = self.run_sequence([["a"], ["a"]])
        self.assertEqual(state["stop_reason"], "repeated_candidate")
        self.assertEqual(state["best_attempt"], 0)

    def test_two_no_progress_rounds_stop(self):
        _, state = self.run_sequence([["a"], ["b"], []])
        self.assertEqual(state["stop_reason"], "no_progress")
        self.assertEqual(state["best_attempt"], 0)

    def test_regression_with_more_passes_is_not_checkpointed(self):
        _, state = self.run_sequence([["a"], ["b", "c"]], max_repairs=1)
        self.assertEqual(state["best_attempt"], 0)
        self.assertFalse(state["attempts"][1]["accepted"])

    def test_budget_stops_before_second_call(self):
        backend, state = self.run_sequence([["a"]], max_output_tokens=100, output_token_budget=100)
        self.assertEqual(len(backend.prompts), 1)
        self.assertEqual(state["stop_reason"], "output_token_budget")

    def test_backend_error_is_recorded(self):
        with self.assertRaises(IndexError):
            self.run_sequence([])
        state = json.loads((Path(self.tmp.name) / "result.json").read_text())
        self.assertEqual(state["status"], "error")
        self.assertTrue((Path(self.tmp.name) / "attempts/00/backend-error.json").exists())

    def test_maximum_repairs_enforced(self):
        with self.assertRaises(ValueError):
            self.run_sequence([], max_repairs=6)

    def test_infrastructure_failure_does_not_call_model(self):
        backend = FakeBackend([])
        with patch.object(FakeEnvironment, "run", return_value={"status": "execution_error", "rows": []}):
            with self.assertRaisesRegex(RuntimeError, "Infrastructure preflight"):
                run_task("levenshtein", backend, directory=Path(self.tmp.name), modes=("cpython",))
        self.assertEqual(backend.prompts, [])


if __name__ == "__main__":
    unittest.main()
