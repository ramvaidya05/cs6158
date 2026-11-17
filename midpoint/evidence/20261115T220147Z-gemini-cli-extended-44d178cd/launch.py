import os,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from migration_lab.backends import GeminiBackend
from migration_lab.budget import SpendBudget
from migration_lab.protocol import FrozenSuite
from migration_lab.experiments import run_experiment,archive_run
from migration_lab.storage import new_run,save_json
for line in Path('.env').read_text().splitlines():
 name,_,value=line.partition('=')
 if name.strip()=='GEMINI_API_KEY': os.environ['GEMINI_API_KEY']=value.strip().strip('\"\x27')
previous=Path('runs/20261115T215510Z-experiment-9d8225e6')
remaining=1-json.loads((previous/'spend.json').read_text())['accounted_usd']
class LongerRequest(GeminiBackend):
 def generate(self,*args,**kwargs):
  kwargs['timeout']=300
  return super().generate(*args,**kwargs)
backend=LongerRequest('gemini-3.8-flash','medium',SpendBudget(remaining,.75,3.75))
backend.identity['request_timeout_seconds']=300
folder=new_run('gemini-cli-extended')
save_json(folder/'protocol-adjustment.json',{'previous_run':str(previous),'reason':'Two timeouts and one MAX_TOKENS response; no candidate evaluated','request_timeout_seconds':300,'output_tokens':32768,'remaining_reservation_usd':remaining,'shared_total_limit_usd':1})
(folder/'launch.py').write_text(Path(__file__).read_text())
print('Artifacts:',folder,flush=True)
path,result=run_experiment(backend,FrozenSuite('runs/commons-cli-live-preparation/suite.json'),tasks=('commons_cli',),trials=1,max_repairs=1,timeout=90,max_seconds=900,max_output_tokens=32768,output_token_budget=65536,directory=folder)
print('Archived:',archive_run(path),flush=True)
print(json.dumps({'arms':result['arms'],'usage':result['usage']},indent=2))
