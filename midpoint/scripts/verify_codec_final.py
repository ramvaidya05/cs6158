"""Final assisted Hex qualification, including all Java char digit values."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from migration_lab.storage import ROOT,new_run,save_json,sha256
from migration_lab.environment import EnvironmentAgent
from migration_lab.isolation import ContainerExecutor
from migration_lab.process import execute
from migration_lab.experiments import archive_run
from scripts.codec_hex_pilot import score

def main():
    folder=new_run('codec-final-validation')
    candidate=ROOT/'translations/commons_codec_hex.py'
    frozen=ROOT/'evidence/20261121T230658Z-codec-hex-pilot/frozen-suite.json'
    suite=json.loads(frozen.read_text())
    env=EnvironmentAgent(60,ContainerExecutor())
    result={'provenance':'model translation with developer Unicode portability fix','model_calls':0,'candidate_sha256':sha256(candidate),'suite_sha256':sha256(frozen),'scores':{}}
    (folder/'candidate.py').write_text(candidate.read_text())
    for split in ('visible','holdout'):
        result['scores'][split]=score(env,candidate,suite['cases'][split],suite['reference'][split],split,folder)
    java='class CodecDigits { public static void main(String[] a) { for(int i=0;i<65536;i++) System.out.print((char)(66+Character.digit((char)i,16))); } }'
    (folder/'CodecDigits.java').write_text(java)
    oracle=execute(['java',str(folder/'CodecDigits.java')],timeout=30)
    if oracle['exit_code']!=0 or len(oracle['stdout'])!=65536:raise RuntimeError('Character oracle failed')
    save_json(folder/'character-oracle.json',oracle)
    probe=folder/'character-probe.py'
    probe.write_text(candidate.read_text()+'\ndef run(operation, data, lower=True):\n    return "".join(chr(66+_character_digit_radix_16(i)) for i in range(65536))\n')
    rows=[{'id':'all-java-chars','task':'commons_codec_hex','operation':'encode','data':[],'lower':True}]
    result['character_domain']={}
    for mode in ('cpython','graal'):
        observed=env.run(mode,rows,folder/'character-domain'/mode,probe)
        value=observed['rows'][0].get('value','') if observed['status']=='completed' else ''
        result['character_domain'][mode]={'total':65536,'passed':sum(a==b for a,b in zip(oracle['stdout'],value)) if len(value)==65536 else 0}
    result['passed']=all(v['passed']==v['total'] for s in result['scores'].values() for v in s.values()) and all(v['passed']==65536 for v in result['character_domain'].values())
    save_json(folder/'summary.json',result)
    print(archive_run(folder));print('PASS',result['passed']);print(result['character_domain'])
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
