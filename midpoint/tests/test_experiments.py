import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from migration_lab.backends import BackendError, OpenAIResponsesBackend, parse_response, InitialResponseBackend, AvailabilityGuard
from migration_lab.budget import SpendBudget
from migration_lab.process import execute
from migration_lab.protocol import evaluation_cases
from migration_lab.experiments import aggregate, ARMS
from migration_lab.storage import save_json
from migration_lab.controller import run_task
from test_core import FakeBackend, FakeEnvironment, FakeTestsuite


class AdapterFailures(unittest.TestCase):
    def test_provider_guard_stops_after_three_unavailable_calls_without_retry(self):
        backend = FakeBackend([])
        with patch.object(backend, 'generate', side_effect=BackendError('unavailable', 'http_error', http_status=503)) as generate:
            guard = AvailabilityGuard(backend)
            for _ in range(3):
                with self.assertRaises(BackendError): guard.generate('x', 0, 'prompt')
            with self.assertRaises(BackendError) as cm: guard.generate('x', 0, 'prompt')
            self.assertEqual(cm.exception.kind, 'provider_circuit_open')
            self.assertEqual(generate.call_count, 3)
            self.assertEqual(guard.stop['consecutive_failures'], 3)

    def test_provider_guard_resets_on_success_and_stops_on_auth(self):
        backend = FakeBackend([])
        responses = [BackendError('timeout', 'timeout'), {'code': 'x'},
                     BackendError('timeout', 'timeout'), BackendError('auth', 'authentication')]
        with patch.object(backend, 'generate', side_effect=responses):
            guard = AvailabilityGuard(backend, failure_limit=2)
            with self.assertRaises(BackendError): guard.generate('x',0,'prompt')
            guard.generate('x',0,'prompt')
            with self.assertRaises(BackendError): guard.generate('x',0,'prompt')
            self.assertIsNone(guard.stop)
            with self.assertRaises(BackendError): guard.generate('x',0,'prompt')
            self.assertEqual(guard.stop['reason'], 'authentication')

    def test_http_failures_are_classified_and_sanitized(self):
        for code, kind in ((401, 'authentication'), (403, 'access_denied'), (429, 'rate_limit'), (500, 'http_error')):
            with self.subTest(code=code), patch.dict(os.environ, OPENAI_API_KEY='secret-sentinel'), \
                    patch('urllib.request.urlopen', side_effect=HTTPError('url', code, 'secret-sentinel', {}, io.BytesIO(b'secret-sentinel'))):
                with self.assertRaises(BackendError) as cm:
                    OpenAIResponsesBackend('test').generate('x', 0, 'prompt')
                self.assertEqual(cm.exception.kind, kind)
                self.assertNotIn('secret-sentinel', str(cm.exception) + str(cm.exception.details))

    def test_timeouts_and_transport_errors(self):
        for error, kind in ((TimeoutError(), 'timeout'), (URLError(TimeoutError()), 'timeout'), (URLError('offline'), 'transport')):
            with patch.dict(os.environ, OPENAI_API_KEY='sentinel'), patch('urllib.request.urlopen', side_effect=error):
                with self.assertRaises(BackendError) as cm:
                    OpenAIResponsesBackend('test').generate('x', 0, 'prompt')
                self.assertEqual(cm.exception.kind, kind)

    def test_refusal_incomplete_and_schema_are_distinct(self):
        for raw, kind in (({'status': 'incomplete'}, 'incomplete'),
                ({'status': 'completed', 'output': [{'type':'message','content':[{'type':'refusal'}]}]}, 'refusal'),
                ({'status': 'completed', 'output': [{'type':'message','content':[{'type':'output_text','text':'{"code":"x"}'}]}]}, 'malformed_output'),
                ([], 'malformed_output')):
            with self.assertRaises(BackendError) as cm:
                parse_response(raw)
            self.assertEqual(cm.exception.kind, kind)

    def test_failed_parse_retains_usage_and_raw_evidence(self):
        raw = {'status':'incomplete', 'usage':{'input_tokens':10,'output_tokens':30}}
        budget = SpendBudget(1, 4, 20)
        with patch.dict(os.environ, OPENAI_API_KEY='sentinel'), patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(raw).encode())):
            with self.assertRaises(BackendError) as cm:
                OpenAIResponsesBackend('test', budget=budget).generate('x',0,'prompt')
        self.assertEqual(cm.exception.raw_response, raw)
        self.assertTrue(budget.entries[0]['usage_known'])

    def test_budget_blocks_before_network_and_retains_unknown_charge(self):
        budget = SpendBudget(0.001, 4, 20)
        with patch.dict(os.environ, OPENAI_API_KEY='sentinel'), patch('urllib.request.urlopen') as transport:
            with self.assertRaises(BackendError):
                OpenAIResponsesBackend('test', budget=budget).generate('x',0,'prompt')
            transport.assert_not_called()
        budget = SpendBudget(1, 4, 20)
        with patch.dict(os.environ, OPENAI_API_KEY='sentinel'), patch('urllib.request.urlopen', side_effect=TimeoutError()):
            with self.assertRaises(BackendError):
                OpenAIResponsesBackend('test', budget=budget).generate('x',0,'prompt')
        self.assertGreater(budget.record()['accounted_usd'], 0)
        self.assertFalse(budget.entries[0]['usage_known'])

    def test_initial_reuse_checks_prompt_and_makes_no_call(self):
        backend = FakeBackend([])
        paired = InitialResponseBackend(backend, {'code':'x','metadata':{}}, 'original')
        self.assertTrue(paired.generate('x',0,'original')['metadata']['reused_initial'])
        self.assertEqual(backend.prompts, [])
        with self.assertRaises(BackendError):
            paired.generate('x',0,'changed')


class ExperimentTests(unittest.TestCase):
    def test_provider_stop_retains_unrun_trials_in_denominator(self):
        from migration_lab.experiments import run_experiment
        from types import SimpleNamespace
        class Suite:
            def __init__(self, path): self.path = path
            def identity(self): return {'counts': {'levenshtein': {'visible': 2, 'holdout': 3}}}
        backend = SimpleNamespace(identity={'provenance': 'live_model'})
        calls = []
        def generate(*args, **kwargs):
            calls.append(1)
            raise BackendError('temporary failure', 'timeout')
        backend.generate = generate
        def run(task, backend, **kwargs):
            folder = kwargs['directory']
            save_json(folder/'manifest.json', {'backend': backend.identity})
            try:
                backend.generate(task,0,'prompt')
            except BackendError as exc:
                save_json(folder/'attempts/00/backend-error.json', {'kind': exc.kind})
                raise
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'suite.json').write_text('{}')
            with patch('migration_lab.experiments.FrozenSuite', Suite), \
                    patch('migration_lab.experiments.ContainerExecutor'), \
                    patch('migration_lab.experiments.EnvironmentAgent'), \
                    patch('migration_lab.experiments.run_task', side_effect=run), \
                    patch('migration_lab.experiments.score_selected'):
                folder, report = run_experiment(backend, Suite(path/'suite.json'), trials=5, directory=path/'run')
            self.assertEqual(len(calls),3)
            self.assertEqual(report['usage']['model_calls'],3)
            self.assertEqual(report['arms']['one_shot']['admitted_task_trials'],5)
            self.assertTrue((folder/'provider-stop.json').exists())
            self.assertEqual(json.loads((folder/'trial-004/levenshtein/one_shot/result.json').read_text())['not_run_reason'], 'provider_circuit_open')

    def test_output_flood_is_bounded_and_stopped(self):
        result = execute([sys.executable, '-c', 'while True: print("x"*10000)'], output_limit=1000, timeout=5)
        self.assertTrue(result['output_truncated'])
        self.assertLessEqual(len(result['stdout']), 1000)
        self.assertLess(result['elapsed_seconds'], 5)

    def test_evaluation_strata_and_seeds(self):
        a = evaluation_cases('levenshtein', 1)
        self.assertEqual(a, evaluation_cases('levenshtein',1))
        self.assertNotEqual(a, evaluation_cases('levenshtein',2))
        self.assertIn(2147483647, [x['parameter'] for x in a])
        self.assertTrue(any('🚀' in (x['a'] or '') for x in a))

    def test_live_code_refused_without_isolation(self):
        backend = FakeBackend([])
        backend.identity = {'provenance':'live_model'}
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(RuntimeError, 'isolation'):
            run_task('levenshtein', backend, directory=Path(tmp))
        self.assertEqual(backend.prompts, [])

    def test_environment_repair_consumes_shared_budget_and_is_logged(self):
        class RepairEnvironment(FakeEnvironment):
            def __init__(self, timeout): self.fixed = False
            def run(self, *args):
                return {'status':'completed','rows':[{'value':0}]} if self.fixed else {'status':'execution_error','rows':[]}
            def remediate(self, mode, result):
                self.fixed = True
                return {'action':'test_repair'}
        with tempfile.TemporaryDirectory() as tmp, patch('migration_lab.controller.TestsuiteAgent', FakeTestsuite):
            backend = FakeBackend([['a'], ['a','b']])
            _, state = run_task('levenshtein',backend,max_repairs=1,environment_repairs=True,
                                environment=RepairEnvironment(1),modes=('cpython',),directory=Path(tmp))
            self.assertEqual(len(backend.prompts),1)
            self.assertEqual(len(state['environment_actions']),1)
            self.assertEqual(state['stop_reason'],'shared_repair_budget')

    def test_failure_inclusive_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            plan = {'backend':{'provenance':'synthetic_fixture'},'study':'test',
                    'suite':{'counts':{'levenshtein':{'visible':26,'holdout':140}}},
                    'runtimes':['cpython','graal'], 'planned_runs':[
                        {'trial':0,'task':'levenshtein','arm':arm,'path':arm} for arm in ARMS]}
            save_json(p/'experiment.json',plan)
            save_json(p/'code_repair/result.json',{'status':'error'})
            report = aggregate(p)
            for arm in ARMS:
                self.assertEqual(report['arms'][arm]['admitted_task_trials'],1)
                self.assertEqual(report['arms'][arm]['task_pass_rate'],0)
                self.assertEqual(report['arms'][arm]['runtimes']['graal']['holdout']['total'],140)
                self.assertEqual(report['arms'][arm]['runtimes']['graal']['holdout']['unvalidated'],140)
                self.assertIsNone(report['arms'][arm]['pass_rate_among_completed'])
            self.assertEqual(report['repair_opportunities']['initials_with_visible_failures'],0)
            self.assertTrue(all(not p['comparable'] for p in report['paired_changes']))

    def test_per_task_reporting_distinguishes_repair_from_ceiling_and_failed_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = ('levenshtein', 'normalized', 'jaro_winkler')
            planned = [{'trial': 0, 'task': task, 'arm': arm, 'path': task+'/'+arm}
                       for task in tasks for arm in ARMS]
            save_json(root/'experiment.json', {'backend': {'provenance': 'live_model'}, 'study': 'test',
                'suite': {'counts': {t: {'visible': 2, 'holdout': 3} for t in tasks}},
                'runtimes': ['cpython', 'graal'], 'planned_runs': planned})
            for item in planned:
                if item['task'] == 'jaro_winkler':
                    state = {'status': 'error'}
                else:
                    good = item['task'] == 'normalized' or item['arm'] != 'one_shot'
                    state = {'status': 'completed', 'validated': good}
                    for split, n in (('visible', 2), ('holdout', 3)):
                        state['selected_'+split] = {'all_pass': good, 'runtimes': {
                            m: {'status': 'completed', 'passed': n if good else 1}
                            for m in ('cpython','graal')}}
                save_json(root/item['path']/'result.json', state)
            report = aggregate(root)
            self.assertEqual(report['arms']['one_shot']['task_pass_rate'], 1/3)
            self.assertEqual(report['arms']['one_shot']['pass_rate_among_completed'], 1/2)
            opportunities = report['repair_opportunities']
            self.assertEqual(opportunities['initials_with_visible_failures'], 1)
            self.assertEqual(opportunities['initials_passing_visible'], 1)
            self.assertEqual(opportunities['arms']['code_repair']['eligible_pairs_fully_recovered'], 1)
            self.assertEqual(report['by_task']['normalized']['repair_opportunities']['initials_with_visible_failures'], 0)
            self.assertEqual(report['by_task']['jaro_winkler']['arms']['one_shot']['completed_task_trials'], 0)

    def test_gemini_credentials_are_provider_specific_and_not_shell_evaluated(self):
        from migration_lab.credentials import load_key
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            path = Path(tmp)/'key'
            path.write_text('GEMINI_API_KEY=AQ.test-credential\n')
            load_key(path, provider='gemini')
            self.assertEqual(os.environ['GEMINI_API_KEY'], 'AQ.test-credential')
            self.assertNotIn('OPENAI_API_KEY', os.environ)
            del os.environ['GEMINI_API_KEY']
            for text in ('OPENAI_API_KEY=sk-test', '$(touch stolen)', 'a\nb'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load_key(path, provider='gemini')
            with patch('getpass.getpass', return_value='AQ.prompt-only'):
                load_key(Path(tmp)/'missing', provider='gemini', prompt=True)
            self.assertEqual(os.environ['GEMINI_API_KEY'], 'AQ.prompt-only')
            self.assertFalse((Path(tmp)/'missing').exists())

    def test_failed_repair_preserves_checkpoint_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp, patch('migration_lab.controller.EnvironmentAgent', FakeEnvironment), patch('migration_lab.controller.TestsuiteAgent',FakeTestsuite):
            backend=FakeBackend([['a']])
            _,state=run_task('levenshtein',backend,modes=('cpython',),directory=Path(tmp))
            self.assertEqual(state['best_attempt'],0)
            self.assertEqual(state['stop_reason'],'backend_error')
            self.assertTrue((Path(tmp)/'attempts/01/backend-error.json').exists())
            self.assertTrue((Path(tmp)/'selection.json').exists())

    def test_all_arm_selections_precede_holdout_and_failures_do_not_abort_batch(self):
        from migration_lab.protocol import FrozenSuite
        from migration_lab.experiments import run_experiment
        from migration_lab.benchmark import TASKS, verify_vendor
        from migration_lab.storage import ROOT, sha256
        observations=[]
        class TracedSuite(FakeTestsuite):
            def reference(self, rows, directory):
                if 'holdout' in rows[0]['id']:
                    observations.append('holdout')
                return super().reference(rows,directory)
        class Env(FakeEnvironment):
            def __init__(self, timeout, executor=None): pass
        class Flaky(FakeBackend):
            def generate(self, *args, **kwargs):
                observations.append('generate')
                if observations.count('generate') == 1:
                    raise BackendError('recorded failure')
                return super().generate(*args, **kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            payload={'schema':1,'source':verify_vendor(),'comparator_sha256':sha256(ROOT/'migration_lab/evaluation.py'),
                     'policy':'test','tasks':{}}
            for task in TASKS:
                payload['tasks'][task]={}
                for split in ('visible','holdout'):
                    rows=[{'id':f'{split}-{i}','task':task,'a':f'{split}-secret-{i}','b':'','operation':'distance'} for i in range(2)]
                    payload['tasks'][task][split]={'cases':rows,'reference':[{'id':r['id'],'status':'ok','value':1} for r in rows]}
            save_json(root/'suite.json',payload)
            backend=Flaky([['a','b']])
            with patch('migration_lab.experiments.ContainerExecutor'), patch('migration_lab.experiments.EnvironmentAgent',Env), patch('migration_lab.controller.TestsuiteAgent',TracedSuite):
                directory,result=run_experiment(backend,FrozenSuite(root/'suite.json'),trials=2,directory=root/'experiment')
            self.assertEqual(len(result['runs']),6)
            self.assertEqual(result['arms']['one_shot']['tasks_passing'],1)
            self.assertTrue(all(x=='holdout' for x in observations[observations.index('holdout'):]))
            self.assertTrue(all('holdout-secret' not in p for p in backend.prompts))
            selections=json.loads((directory/'selections-frozen.json').read_text())
            self.assertEqual(len(selections),3)
            # Both iterative arms use the byte-identical initial candidate.
            files=list((directory/'trial-001/levenshtein').glob('*/attempts/00/candidate.py'))
            self.assertEqual(len({p.read_text() for p in files}),1)

    def test_quota_code_allowlist_does_not_log_body(self):
        for code in ('insufficient_quota','credit_balance_exhausted','organization_spend_limit_exceeded',
                     'project_spend_limit_exceeded','organization_usage_limit_exceeded'):
            raw={'error':{'code':code,'message':'secret-sentinel'}}
            error=HTTPError('url',429,'error',{},io.BytesIO(json.dumps(raw).encode()))
            with patch.dict(os.environ, OPENAI_API_KEY='sentinel'),patch('urllib.request.urlopen',side_effect=error):
                with self.assertRaises(BackendError) as cm:
                    OpenAIResponsesBackend('test').generate('x',0,'prompt')
                self.assertEqual(cm.exception.kind,'quota')
                self.assertEqual(cm.exception.details['provider_code'],code)
                self.assertNotIn('secret-sentinel',str(cm.exception.details))

    def test_nonfinite_execution_budgets_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for timeout in (float('nan'),float('inf'),0,-1):
                with self.assertRaises(ValueError):
                    run_task('levenshtein',FakeBackend([]),timeout=timeout,directory=Path(tmp))

    def test_local_key_loader_never_evaluates_shell(self):
        from migration_lab.credentials import load_key
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{},clear=True):
            p=Path(tmp)/'key'
            p.write_text('OPENAI_API_KEY=sk-test-only\n')
            load_key(p)
            self.assertEqual(os.environ['OPENAI_API_KEY'],'sk-test-only')
            os.environ.pop('OPENAI_API_KEY')
            p.write_text('export OPENAI_API_KEY=$(touch stolen)')
            with self.assertRaises(ValueError): load_key(p)
            self.assertNotIn('OPENAI_API_KEY',os.environ)

    def test_frozen_suite_tampering_is_rejected(self):
        from migration_lab.protocol import FrozenSuite
        from migration_lab.storage import ROOT, sha256
        from migration_lab.benchmark import TASKS, verify_vendor
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'suite.json'
            row={'id':'one','task':'levenshtein'}
            entry={'cases':[row],'reference':[{'id':'one','status':'ok','value':0}]}
            save_json(p,{'schema':1,'source':verify_vendor(),'comparator_sha256':sha256(ROOT/'migration_lab/evaluation.py'),
                         'policy':'test','tasks':{task:{'visible':entry,'holdout':entry} for task in TASKS}})
            suite=FrozenSuite(p)
            p.write_text(p.read_text()+'\n')
            with self.assertRaisesRegex(RuntimeError,'changed'):
                suite.cases('levenshtein','holdout')
