"""Prospective paired code-only versus runtime-diagnosis repair study."""
import json, os, random, sys, time
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


def fresh_cases():
    visible = cases()['visible']
    held = []
    rng = random.Random(2026112201)
    values = [''.join(str(rng.randrange(10)) for _ in range(rng.randrange(1, 100))) for _ in range(40)]
    for base in (0x660, 0x6f0, 0x966, 0xff10):
        for _ in range(5):
            values.append(''.join(chr(base+rng.randrange(10)) for _ in range(rng.randrange(2, 15))))
    values += ['\ud800', '\udfff1', '1\ud800', '\U0001d7d91', '\u200312', '\x0012', '0'*73, '9'*257]
    for value in values:
        for operation in ('calculate','isValid'):
            held.append({'id':f'paired-held-{len(held)}','task':'commons_validator_luhn','operation':operation,'data':value})
    return {'visible':visible, 'holdout':held}


def all_pass(scores):
    return all(s['status']=='completed' and s['passed']==s['total'] for s in scores.values())


def main():
    verify_source()
    directory = new_run('validator-paired-diagnosis')
    started = time.monotonic()
    result = {'status':'started','trials':[], 'interpretation':'fresh paired live trials; source-runtime portability, not injected infrastructure recovery'}
    save_json(directory/'plan.json', {'trials':3,'model':'gemini-3.5-flash','thinking':'low',
      'max_output_tokens_per_call':4096,'max_calls':9,'usd_cap':0.50,'per_trial_cap':0.50/3,
      'arms':['code_only','diagnosis'],'max_repairs_per_arm':1,'seed':2026112201,
      'primary_endpoint':'all visible and holdout cases pass in both runtimes',
      'selection':'visible-only, no per-case regressions in either runtime',
      'holdout_evaluation':'after all trial selections are frozen',
      'diagnosis':'capability probe plus Java digit contract; no deterministic candidate edits',
      'order':'alternated by trial; shared initial candidate; fresh independent trial requests'})
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
        load_key(provider='gemini')
        for trial in range(3):
            folder=directory/f'trial-{trial}'
            budget=SpendBudget(0.50/3,1.5,9,folder/'spend.json');budgets.append(budget)
            backend=GeminiBackend('gemini-3.5-flash','low',budget)
            entry={'trial':trial,'arms':{},'calls':[]};result['trials'].append(entry)
            def generate(label, question):
                save_json(folder/label/'prompt.json',{'prompt':question})
                record={'label':label};entry['calls'].append(record)
                response=backend.generate('commons_validator_luhn',len(entry['calls'])-1,question,timeout=60,max_output_tokens=4096)
                save_json(folder/label/'response.json',response)
                record['metadata']=response['metadata']
                path=folder/label/'candidate.py';path.write_text(response['code'])
                return path
            initial=generate('initial',prompt())
            baseline=score(env,initial,suite['visible'],reference['visible'],'visible',folder/'initial')
            entry['baseline_visible']=baseline
            order=('code_only','diagnosis') if trial%2==0 else ('diagnosis','code_only')
            for arm in order:
                state={'selected':'initial/candidate.py','accepted':False,'repair_calls':0};entry['arms'][arm]=state
                if not all_pass(baseline):
                    failures=[f for m in ('cpython','graal') for f in baseline[m]['failures']]
                    question=prompt(initial.read_text(),failures) if arm=='code_only' else repair_prompt(initial.read_text(),baseline,diagnosis)
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
        print('Full passes:',{a:sum(t['arms'].get(a,{}).get('full_pass',False) for t in result['trials']) for a in ('code_only','diagnosis')},flush=True)
    return 0 if result['status']=='completed' else 1

if __name__=='__main__':raise SystemExit(main())
