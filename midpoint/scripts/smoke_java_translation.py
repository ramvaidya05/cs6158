"""One tiny live Java-to-Python smoke test using the shared adapter and Docker evaluator."""
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from migration_lab.backends import GeminiBackend,BackendError
from migration_lab.budget import SpendBudget
from migration_lab.environment import EnvironmentAgent
from migration_lab.evaluation import TestsuiteAgent
from migration_lab.isolation import ContainerExecutor
from migration_lab.process import execute
from migration_lab.storage import new_run,save_json,protected_hashes
from migration_lab.controller import assert_unchanged
from migration_lab.experiments import archive_run

SOURCE='''public final class TinyAdd {
    public static int add(int a, int b) {
        return a + b;
    }
}
'''

def main():
    if not os.environ.get('GEMINI_API_KEY'):
        for line in (ROOT/'.env').read_text().splitlines():
            name,_,value=line.partition('=')
            if name.strip()=='GEMINI_API_KEY':os.environ['GEMINI_API_KEY']=value.strip().strip('\"\x27')
    if not os.environ.get('GEMINI_API_KEY'):raise ValueError('Gemini key required')
    folder=new_run('tiny-java-smoke');print('Artifacts:',folder,flush=True)
    (folder/'TinyAdd.java').write_text(SOURCE)
    pairs=[(0,0),(2,3),(-7,4),(-3,-9),(2147483647,0),(2147483647,1),(-2147483648,-1),(-2147483648,2147483647)]
    rows=[{'id':f'add-{i}','task':'tiny_java_add','a':str(a),'b':str(b),'operation':'add','parameter':None} for i,(a,b) in enumerate(pairs)]
    save_json(folder/'cases.json',rows)
    driver='class Oracle { public static void main(String[] args) {\n'+''.join(f'System.out.println(TinyAdd.add({a}, {b}));\n' for a,b in pairs)+'}}\n'+SOURCE.replace('public final class','final class')
    (folder/'Oracle.java').write_text(driver)
    oracle=execute(['java',str(folder/'Oracle.java')],timeout=30);save_json(folder/'oracle-execution.json',oracle)
    if oracle['exit_code']!=0:raise RuntimeError('Java oracle failed')
    values=[int(line) for line in oracle['stdout'].splitlines()]
    reference=[{'id':case['id'],'status':'ok','value':value} for case,value in zip(rows,values,strict=True)]
    save_json(folder/'reference.json',reference)
    environment=EnvironmentAgent(60,ContainerExecutor())
    for mode in ('cpython','graal'):
        probe=environment.run(mode,[{'id':'preflight','task':'levenshtein','a':'','b':'','operation':'distance','parameter':None}],folder/'preflight'/mode,ROOT/'fixtures/preflight.py')
        if probe['status']!='completed' or probe['rows'][0].get('value')!=0:raise RuntimeError('Container preflight failed: '+mode)
    prompt='Translate this Java file to a standalone Python module. Define run(a, b, operation, parameter=None). a and b are decimal strings representing Java signed 32-bit integers. operation is always add. Return the integer result of TinyAdd.add, preserving Java int overflow. No imports or external services are needed. Return the required JSON object with code and explanation; keep the explanation to one sentence.\n\n'+SOURCE
    (folder/'prompt.txt').write_text(prompt)
    backend=GeminiBackend('gemini-3.8-flash','low',SpendBudget(.05,.75,3.75,folder/'spend.json'))
    guard=protected_hashes()
    save_json(folder/'manifest.json',{'purpose':'Single-file smoke test; not benchmark accuracy','backend':backend.identity,'model_timeout':60,'max_output_tokens':2048,'prompt_bytes':len(prompt.encode()),'environment':environment.identity() if hasattr(environment,'identity') else environment.executor.identity(),'protected_hashes':guard})
    result={'purpose':'Single-file live translation smoke test','status':'error','validated':False}
    try:
        print('Calling Gemini for TinyAdd.java...',flush=True)
        response=backend.generate('tiny_java_add',0,prompt,timeout=60,max_output_tokens=2048)
        save_json(folder/'response.json',response)
        candidate=folder/'candidate.py';candidate.write_text(response['code'])
        assert_unchanged(guard)
        evaluation=TestsuiteAgent(environment).evaluate(candidate,rows,reference,('cpython','graal'),folder/'evaluation')
        assert_unchanged(guard)
        result.update(status='completed',validated=evaluation['all_pass'],evaluation=evaluation,metadata=response['metadata'])
    except BackendError as exc:
        result.update(kind=exc.kind,message=str(exc),details=exc.details)
        save_json(folder/'backend-error.json',{'kind':exc.kind,'details':exc.details,'raw_response':getattr(exc,'raw_response',None)})
    finally:
        save_json(folder/'summary.json',result)
        print('Archived:',archive_run(folder),flush=True)
        print(json.dumps(result,indent=2))
    return 0 if result['validated'] else 1
if __name__=='__main__':raise SystemExit(main())
