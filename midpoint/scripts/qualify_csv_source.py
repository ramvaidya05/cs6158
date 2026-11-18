"""Development-only CSV Java oracle qualification; no model or candidate execution."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from migration_lab.environment import EnvironmentAgent
from migration_lab.experiments import archive_run
from migration_lab.storage import new_run,save_json,sha256


def main():
    base=ROOT/'vendor/commons-csv'
    manifest=json.loads((base/'SOURCE.json').read_text())
    for name,digest in manifest['files'].items():
        if sha256(base/name)!=digest: raise RuntimeError('CSV source differs from pinned archive: '+name)
    rows=[
        {'operation':'parse','text':'a,"b,b","line1\nline2",\n'},
        {'operation':'parse','text':'"unterminated'},
        {'operation':'parse','text':'a,b\n\n,c\n','config':{'ignore_empty_lines':False}},
        {'operation':'parse','text':' a ;NULL;" b "\n','config':{'delimiter':';','trim':True,'null_string':'NULL'}},
        {'operation':'parse','text':'α,🚀\r\n"quote""inside",end'},
        {'operation':'print','records':[['a,b','say "hi"','']]},
        {'operation':'print','records':[[None,'NULL','a\nb']], 'config':{'null_string':'NULL','record_separator':'\n'}},
        {'operation':'parse','text':'','config':{'trim':1}},
    ]
    rows=[{'id':f'csv-development-{i:02}','task':'commons_csv',**row} for i,row in enumerate(rows)]
    directory=new_run('csv-source-qualification')
    environment=EnvironmentAgent(60)
    first=environment.run('reference',rows,directory/'oracle-first')
    second=environment.run('reference',rows,directory/'oracle-repeat')
    if first['status']!='completed' or second['status']!='completed' or first['rows']!=second['rows']:
        raise RuntimeError('CSV reference failed or was nondeterministic; see '+str(directory))
    save_json(directory/'summary.json',{'provenance':'Java source qualification; no translated candidate',
        'source_artifact':manifest['artifact'],'source_manifest_sha256':sha256(base/'SOURCE.json'),
        'draft_contract_sha256':sha256(ROOT/'benchmarks/commons_csv.json'),'cases':len(rows),
        'repeated_oracle_equal':True,'model_calls':0,'evaluation_split':'development only; not a frozen benchmark',
        'rows':first['rows']})
    print('Archived:',archive_run(directory))


if __name__=='__main__': main()
