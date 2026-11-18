"""Visible-only synthetic CSV mutation checks in both Docker runtimes.

The independent stdlib probe is deliberately incomplete. Detection counts only
new failures among cases it passed; no model accuracy or holdout tuning claim.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from migration_lab.protocol import FrozenSuite
from migration_lab.environment import EnvironmentAgent
from migration_lab.evaluation import TestsuiteAgent
from migration_lab.isolation import ContainerExecutor
from migration_lab.storage import new_run,save_json,sha256
from migration_lab.experiments import archive_run

MUTATIONS={
    'split_lines_and_commas': 'def parse_csv(text, config): return [line.split(",") for line in text.splitlines()]',
    'drop_empty_fields': '_old=parse_csv\ndef parse_csv(text, config): return [[v for v in row if v != ""] for row in _old(text, config)]',
    'collapse_null': '_old=parse_csv\ndef parse_csv(text, config): return [["" if v is None else v for v in row] for row in _old(text, config)]',
    'ignore_trim': '_old=parse_csv\ndef parse_csv(text, config): return _old(text, {**config,"trim":False})',
    'reverse_records': '_old=parse_csv\ndef parse_csv(text, config): return list(reversed(_old(text,config)))',
    'wrong_exception': '_old=parse_csv\ndef parse_csv(text, config):\n    try: return _old(text,config)\n    except CSVParseError: raise ValueError("wrong category")',
    'printer_lf_only': '_old=print_csv\ndef print_csv(records, config): return _old(records,config).replace("\\r\\n","\\n")',
    'printer_quote_loss': '_old=print_csv\ndef print_csv(records, config): return _old(records,config).replace(\'""\',\'"\')',
}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--suite',type=Path,required=True);args=parser.parse_args()
    suite=FrozenSuite(args.suite)
    if suite.identity()['profile']!='commons-csv-v1':raise ValueError('CSV v1 suite required')
    rows=suite.cases('commons_csv','visible');reference=suite.reference('commons_csv','visible')
    folder=new_run('csv-qualification');print('Artifacts:',folder,flush=True)
    tester=TestsuiteAgent(EnvironmentAgent(90,ContainerExecutor()))
    source=(ROOT/'fixtures/csv_stdlib_probe.py').read_text();baseline=folder/'baseline.py';baseline.write_text(source)
    before=tester.evaluate(baseline,rows,reference,('cpython','graal'),folder/'baseline')
    report={'provenance':'synthetic fixture; not live inference','suite':suite.identity(),'baseline_sha256':sha256(baseline),
            'baseline':before,'policy':'Visible only; baseline-passing cases lost by each mutation; infrastructure errors do not count','mutations':{}}
    for name,patch in MUTATIONS.items():
        candidate=folder/(name+'.py');candidate.write_text(source+'\n'+patch+'\n')
        after=tester.evaluate(candidate,rows,reference,('cpython','graal'),folder/name)
        report['mutations'][name]={}
        for mode in ('cpython','graal'):
            a,b=before['runtimes'][mode],after['runtimes'][mode]
            lost=sorted(set(a['passed_ids'])-set(b['passed_ids'])) if a['status']==b['status']=='completed' else []
            report['mutations'][name][mode]={'status':b['status'],'detected':bool(lost),'newly_failing_case_ids':lost}
        print(name,{m:r['detected'] for m,r in report['mutations'][name].items()},flush=True)
    report['detected_in_both']=sum(all(r['detected'] for r in modes.values()) for modes in report['mutations'].values())
    report['total_mutants']=len(MUTATIONS)
    save_json(folder/'summary.json',report)
    print('Archived:',archive_run(folder),flush=True)
    return 0 if report['detected_in_both']==len(MUTATIONS) else 1


if __name__=='__main__':raise SystemExit(main())
