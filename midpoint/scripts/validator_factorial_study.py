"""Four-arm factorial pilot; preparation is API-free by default."""
import argparse, json, os, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from migration_lab.backends import GeminiBackend, BackendError
from migration_lab.budget import SpendBudget
from migration_lab.credentials import load_key
from migration_lab.environment import EnvironmentAgent
from migration_lab.isolation import ContainerExecutor
from migration_lab.evaluation import TestsuiteAgent
from migration_lab.runtime_diagnosis import diagnose
from migration_lab.storage import ROOT, new_run, save_json, sha256
from migration_lab.experiments import archive_run
from scripts.validator_luhn_pilot import cases, prompt, score, verify_source
from scripts.validator_runtime_repair import repair_prompt, accepts


ARMS = ('code_only', 'diagnosis_only', 'semantics_only', 'both')


def treatment_prompt(previous, visible, diagnosis, arm):
    if arm not in ARMS:
        raise ValueError('Unknown treatment')
    failures = [f for m in ('cpython', 'graal') for f in visible[m]['failures']]
    question = prompt(previous, failures)
    if arm in ('diagnosis_only', 'both'):
        question += '\nRuntime capability probe:\n' + json.dumps(diagnosis['runtimes'])
    if arm in ('semantics_only', 'both'):
        question += ('\nJava semantic contract: char is a UTF-16 code unit. The following bases '
            'start ten consecutive decimal digits 0..9; all other Java char values are not '
            'decimal digits. This mapping was verified across 65536 Java char values. '
            'You may embed the bases: ' + json.dumps(diagnosis['java_decimal_bases']))
    return question


def fresh_cases():
    from scripts.validator_paired_study import fresh_cases as old_cases
    previous = old_cases()
    excluded = {c['data'] for split in previous.values() for c in split}
    rng = random.Random(2026112202)
    values = []
    while len(values) < 60:
        base = (48, 0x660, 0x6f0, 0x966, 0xff10)[len(values) % 5]
        value = ''.join(chr(base+rng.randrange(10)) for _ in range(rng.randrange(2, 120)))
        if value not in excluded and value not in values:
            values.append(value)
    values += ['\ud8012', '2\udffe', '\ud902', '\U0001d7db8', '\u20047', '\x0073', '0'*91, '9'*311]
    assert not (set(values) & excluded)
    held = [{'id':f'factorial-held-{i}-{operation}', 'task':'commons_validator_luhn',
             'operation':operation, 'data':value}
            for i,value in enumerate(values) for operation in ('calculate','isValid')]
    return {'visible':cases()['visible'], 'holdout':held}


def all_pass(scores):
    return all(s['status']=='completed' and s['passed']==s['total'] for s in scores.values())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Run only with explicit study budget approval')
    args=parser.parse_args()
    verify_source()
    directory = new_run('validator-factorial')
    started = time.monotonic()
    result = {'status':'started','trials':[], 'interpretation':'fresh paired live trials; source-runtime portability, not injected infrastructure recovery'}
    save_json(directory/'plan.json', {'trials':4,'model':'gemini-3.5-flash','thinking':'low',
      'max_output_tokens_per_call':4096,'max_calls':20,'usd_cap':1.60,'per_call_cap':0.08,
      'arms':list(ARMS),'max_repairs_per_arm':1,'seed':2026112202,
      'primary_endpoint':'all visible and holdout cases pass in both runtimes',
      'selection':'visible-only, no per-case regressions in either runtime',
      'holdout_evaluation':'after all trial selections are frozen',
      'diagnosis':'capability probe plus Java digit contract; no deterministic candidate edits',
      'order':'rotating Latin square; each arm occupies each position once; shared initial candidate'})
    budgets = []
    try:
        suite = fresh_cases()
        tester = TestsuiteAgent(EnvironmentAgent())
        reference = {}
        for split in suite:
            reference[split] = tester.reference(suite[split],directory/'oracle'/split)
            if reference[split] != tester.reference(suite[split],directory/'oracle'/(split+'-repeat')):
                raise RuntimeError('Nondeterministic oracle')
        save_json(directory/'frozen-suite.json',{'cases':suite,'reference':reference})
        result['suite_sha256']=sha256(directory/'frozen-suite.json')
        env=EnvironmentAgent(60,ContainerExecutor())
        diagnosis=diagnose(env,directory/'diagnosis')
        if not args.live:
            result['status']='prepared'
            return 0
        load_key(provider='gemini')
        for trial in range(4):
            folder=directory/f'trial-{trial}'
            entry={'trial':trial,'arms':{},'calls':[]};result['trials'].append(entry)
            def generate(label, question):
                save_json(folder/label/'prompt.json',{'prompt':question})
                budget=SpendBudget(0.08,1.5,9,folder/label/'spend.json');budgets.append(budget)
                backend=GeminiBackend('gemini-3.5-flash','low',budget)
                record={'label':label};entry['calls'].append(record)
                response=backend.generate('commons_validator_luhn',len(entry['calls'])-1,question,timeout=60,max_output_tokens=4096)
                save_json(folder/label/'response.json',response)
                record['metadata']=response['metadata']
                path=folder/label/'candidate.py';path.write_text(response['code'])
                return path
            initial=generate('initial',prompt())
            baseline=score(env,initial,suite['visible'],reference['visible'],'visible',folder/'initial')
            entry['baseline_visible']=baseline
            order=ARMS[trial:]+ARMS[:trial]
            for arm in order:
                state={'selected':'initial/candidate.py','accepted':False,'repair_calls':0};entry['arms'][arm]=state
                if not all_pass(baseline):
                    failures=[f for m in ('cpython','graal') for f in baseline[m]['failures']]
                    question=treatment_prompt(initial.read_text(),baseline,diagnosis,arm)
                    state['repair_calls']=1
                    candidate=generate(arm,question)
                    observed=score(env,candidate,suite['visible'],reference['visible'],'visible',folder/arm)
                    state['proposed_visible']=observed
                    state['accepted']=accepts(baseline,observed)
                    if state['accepted']:state['selected']=str(candidate.relative_to(folder))
                state['selected_visible']=state.get('proposed_visible') if state['accepted'] else baseline
                state['selected_sha256']=sha256(folder/state['selected'])
            save_json(directory/'summary.json',result)
            print('Selected trial',trial,flush=True)
        save_json(directory/'selections-frozen.json',[{'trial':t['trial'],'arms':{a:s['selected_sha256'] for a,s in t['arms'].items()}} for t in result['trials']])
        for entry in result['trials']:
            folder=directory/f"trial-{entry['trial']}"
            entry['baseline_holdout']=score(env,folder/'initial/candidate.py',suite['holdout'],reference['holdout'],'holdout',folder/'initial')
            for arm,state in entry['arms'].items():
                state['holdout']=score(env,folder/state['selected'],suite['holdout'],reference['holdout'],'holdout',folder/arm)
                state['full_pass']=all_pass(state['selected_visible']) and all_pass(state['holdout'])
        result['status']='completed'
    except Exception as exc:
        result.update(status='failed',error={'type':type(exc).__name__,'kind':getattr(exc,'kind',None),'message':str(exc)})
    finally:
        os.environ.pop('GEMINI_API_KEY',None)
        result['budgets']=[b.record() for b in budgets]
        result['elapsed_seconds']=round(time.monotonic()-started,3)
        save_json(directory/'summary.json',result)
        print('Archive:',archive_run(directory),flush=True)
        print('Status:',result['status'],result.get('error',''),flush=True)
        print('Full passes:',{a:sum(t['arms'].get(a,{}).get('full_pass',False) for t in result['trials']) for a in ARMS},flush=True)
    return 0 if result['status']=='completed' else 1

if __name__=='__main__':raise SystemExit(main())
