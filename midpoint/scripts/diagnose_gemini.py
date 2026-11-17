"""Tiny curl generation probe: no repository upload or candidate execution."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from migration_lab.storage import new_run,save_json
from migration_lab.budget import SpendBudget
from migration_lab.backends import GeminiBackend

def main():
    key=os.environ.get('GEMINI_API_KEY')
    if not key:
        for line in (ROOT/'.env').read_text().splitlines():
            name,_,value=line.partition('=')
            if name.strip()=='GEMINI_API_KEY':key=value.strip().strip('\"\x27')
    if not key:raise ValueError('Set GEMINI_API_KEY in the environment or midpoint/.env')
    folder=new_run('gemini-curl-diagnosis')
    body={'contents':[{'parts':[{'text':'Reply with the word OK.'}]}],'generationConfig':{'maxOutputTokens':2048,'thinkingConfig':{'thinkingLevel':'low'}}}
    budget=SpendBudget(.02,.75,3.75,folder/'spend.json')
    budget.reserve({'request':body,'max_output_tokens':2048})
    with tempfile.TemporaryDirectory() as temp:
        response=Path(temp)/'response.json';payload=Path(temp)/'request.json';payload.write_text(json.dumps(body))
        command=['curl','--config','-','--silent','--show-error','--connect-timeout','15','--max-time','60','--output',str(response),'--write-out','%{json}','--header','Content-Type: application/json','--data-binary','@'+str(payload),'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent']
        proc=subprocess.run(command,input='header = '+json.dumps('x-goog-api-key: '+key)+'\n',text=True,capture_output=True,timeout=70)
        try:timings=json.loads(proc.stdout)
        except ValueError:timings={}
        result={'purpose':'Tiny transport probe; no benchmark or code execution','curl_exit':proc.returncode,'timings':{k:timings.get(k) for k in ['http_code','time_namelookup','time_connect','time_appconnect','time_starttransfer','time_total','http_version','ssl_verify_result']},'stderr':proc.stderr.replace(key,'[redacted]')}
        if response.exists():
            try:
                raw=json.loads(response.read_text());result['model']=raw.get('modelVersion');result['finish_reasons']=[c.get('finishReason') for c in raw.get('candidates',[])];result['usage']=raw.get('usageMetadata')
                if isinstance(raw.get('error'),dict):
                    result['provider_error']={k:str(raw['error'].get(k,'' )).replace(key,'[redacted]')[:500] for k in ('code','status','message')}
                if result['usage']:budget.settle(0,GeminiBackend.normalize_usage(result['usage']))
            except ValueError:result['response_json_valid']=False
    save_json(folder/'result.json',result);print(folder);print(json.dumps(result,indent=2))
    return 0 if proc.returncode==0 and result['timings'].get('http_code')==200 else 1
if __name__=='__main__':raise SystemExit(main())
