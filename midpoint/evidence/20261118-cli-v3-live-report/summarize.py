from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parents[2]
result={'studies':{},'audit':{},'total_model_calls':0,'total_accounted_usd':0,'resolved_models':[]}
for phase in ('smoke','main','memory'):
    directory=root/'evidence'/{'smoke':'20261118T002250Z-cli-v3-smoke-05baa037','main':'20261118T002418Z-cli-v3-main-e1839f4c','memory':'20261118T003004Z-cli-v3-memory-8ca90532'}[phase]
    spend=json.loads((directory/'spend.json').read_text())
    result['total_accounted_usd']+=spend['accounted_usd']
    result['total_model_calls']+=len(spend['calls'])
    for p in directory.rglob('response.json'):
        meta=json.loads(p.read_text()).get('metadata',{})
        model=meta.get('resolved_model')
        if model and model not in result['resolved_models']:result['resolved_models'].append(model)
    item={'archive':directory.name,'calls':len(spend['calls']),'accounted_usd':spend['accounted_usd'],
          'unknown_usage_calls':sum(not e['usage_known'] for e in spend['calls'])}
    if phase=='smoke':
        state=json.loads((directory/'result.json').read_text())
        item.update(status=state['status'],validated=state['validated'],visible=state['selected_visible']['passed'],holdout=state['selected_holdout']['passed'])
    else:
        summary=json.loads((directory/'summary.json').read_text())
        item['arms']=summary['arms'];item['runs']=[]
        suite=json.loads((directory/'evaluation-suite.json').read_text())
        held_ids=[c['id'] for c in suite['tasks']['commons_cli']['holdout']['cases']]
        for trial in sorted(directory.glob('trial-*')):
            hashes=[]
            for folder in sorted((trial/'commons_cli').iterdir()):
                state=json.loads((folder/'result.json').read_text())
                hashes.append(hashlib.sha256((folder/'attempts/00/candidate.py').read_bytes()).hexdigest())
                selected=json.loads((folder/'selection.json').read_text())
                assert selected['sha256']==hashlib.sha256((folder/'final.py').read_bytes()).hexdigest()
                for p in [*folder.glob('attempts/*/prompt.txt'),*folder.glob('TRANSLATION_FAILURES.md')]:
                    assert not any(case_id in p.read_text() for case_id in held_ids)
                if phase=='memory':
                    assert (folder/'TRANSLATION_FAILURES.md').exists()==(folder.name=='memory_on')
                item['runs'].append({'trial':trial.name,'arm':folder.name,'status':state['status'],'validated':state['validated'],
                    'stop_reason':state['stop_reason'],'best_attempt':state['best_attempt'],
                    'environment_actions':len(state['environment_actions']),
                    'attempts':state['attempts'],'visible_passed':state['selected_visible']['passed'],
                    'holdout_passed':state['selected_holdout']['passed'],
                    'holdout_total':state['selected_holdout']['total']})
            assert len(set(hashes))==1
        result['audit'][phase]={'paired_initials_identical':True,'selected_code_hashes_match':True,'holdout_case_ids_absent_from_prompts_and_history':True,
            'unknown_usage_calls':item['unknown_usage_calls'],
            'budget_blocked_trials':sum(v['repair_budget_blocked_trials'] for v in summary['arms'].values())}
    result['studies'][phase]=item
# Credential scan reports only the boolean outcome, never the key.
key=None
for line in (root/'.env').read_text().splitlines():
    name,_,value=line.partition('=')
    if name.strip()=='GEMINI_API_KEY':key=value.strip().strip('\"\x27')
assert key
for study in result['studies'].values():
    for p in (root/'evidence'/study['archive']).rglob('*'):
        if p.is_file(): assert key.encode() not in p.read_bytes(), 'Credential found in archive'
result['audit']['credential_absent_from_archives']=True
out=root/'evidence/20261118-cli-v3-live-report';out.mkdir(exist_ok=True)
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'checksums.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='checksums.json'},indent=2)+'\n')
print(json.dumps(result,indent=2))
