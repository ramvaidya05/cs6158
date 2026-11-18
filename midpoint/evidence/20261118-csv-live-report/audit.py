from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[2]
result={'phases':{},'total_accounted_usd':0,'total_calls':0,'resolved_models':[]}
keys=[]
for filename in ('.env','.env.gemini'):
    path=root/filename
    if path.exists():
        for line in path.read_text().splitlines():
            name,sep,value=line.partition('=')
            if sep and name.strip().endswith('API_KEY') and value.strip():keys.append(value.strip().strip('\"\x27').encode())
for phase in ('smoke','main','memory'):
    archives = {'smoke': '20261118T023453Z-csv-v1-smoke-eaa5fa4d', 'main': '20261118T023644Z-csv-v1-main-19f9796b', 'memory': '20261118T025213Z-csv-v1-memory-31a71c69'}
    directory=root/'evidence'/archives[phase]
    if not directory.exists():continue
    spend=json.loads((directory/'spend.json').read_text())
    item={'archive':directory.name,'calls':len(spend['calls']),'accounted_usd':spend['accounted_usd'],
          'unknown_usage_calls':sum(not c['usage_known'] for c in spend['calls']),
          'largest_reserved_input_allowance':max(round((c['reserved_usd']*1e6-32768*spend['output_usd_per_million'])/(spend['input_usd_per_million']*1.25)) for c in spend['calls'])}
    result['total_accounted_usd']+=item['accounted_usd'];result['total_calls']+=item['calls']
    held=[c['id'] for c in json.loads((directory/'evaluation-suite.json').read_text())['tasks']['commons_csv']['holdout']['cases']]
    for p in directory.rglob('response.json'):
        model=json.loads(p.read_text()).get('metadata',{}).get('resolved_model')
        if model and model not in result['resolved_models']:result['resolved_models'].append(model)
    folders=[directory] if phase=='smoke' else sorted(directory.glob('trial-*/*/*'))
    item['runs']=[]
    paired={}
    for d in folders:
        state=json.loads((d/'result.json').read_text())
        initial=d/'attempts/00/candidate.py'
        if initial.exists():paired.setdefault(d.parent.parent.name,[]).append(hashlib.sha256(initial.read_bytes()).hexdigest())
        for p in [*d.glob('attempts/*/prompt.txt'),*d.glob('TRANSLATION_FAILURES.md')]:
            assert all(case_id not in p.read_text() for case_id in held)
        if (d/'selection.json').exists():
            selection=json.loads((d/'selection.json').read_text())
            assert selection['sha256']==hashlib.sha256((d/'final.py').read_bytes()).hexdigest()
        if phase=='memory':assert (d/'TRANSLATION_FAILURES.md').exists()==(d.name=='memory_on')
        item['runs'].append({'trial':d.parent.parent.name if phase!='smoke' else 'smoke','arm':d.name if phase!='smoke' else 'one_shot',
            'status':state['status'],'validated':state.get('validated',False),'stop_reason':state.get('stop_reason'),
            'best_attempt':state.get('best_attempt'),'attempts':state.get('attempts',[]),
            'visible_passed':state.get('selected_visible',{}).get('passed'),'visible_total':state.get('selected_visible',{}).get('total'),
            'holdout_passed':state.get('selected_holdout',{}).get('passed'),'holdout_total':state.get('selected_holdout',{}).get('total'),
            'environment_actions':len(state.get('environment_actions',[])),'backend_failure':state.get('backend_failure')})
    assert all(len(set(values))==1 for values in paired.values())
    for p in directory.rglob('*'):
        if p.is_file():assert all(key not in p.read_bytes() for key in keys),'Credential scan failed'
    if phase!='smoke':
        summary=json.loads((directory/'summary.json').read_text());item['arms']=summary['arms'];item['repair_opportunities']=summary['repair_opportunities']
        item['usage']=summary['usage'];item['arm_call_costs']={}
        for arm in summary['arms']:
            entries=[c for c in spend['calls'] if c['allocation'].endswith('/'+arm)]
            item['arm_call_costs'][arm]={'calls':len(entries),'accounted_usd':sum(c['accounted_usd'] for c in entries)}
    item['audit']={'paired_initials_identical':True,'selected_hashes_intact':True,'holdout_case_ids_absent_from_prompts_and_history':True,'configured_credentials_absent':True}
    result['phases'][phase]=item
out=root/'evidence/20261118-csv-live-report';out.mkdir(exist_ok=True)
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
