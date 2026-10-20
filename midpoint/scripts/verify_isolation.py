"""Archive isolation tests and fixture parity on a frozen, evaluator-only suite."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.process import execute
from migration_lab.protocol import FrozenSuite
from migration_lab.environment import EnvironmentAgent
from migration_lab.isolation import ContainerExecutor
from migration_lab.evaluation import TestsuiteAgent
from migration_lab.experiments import archive_run
from migration_lab.storage import new_run, save_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,required=True)
    args=parser.parse_args()
    suite=FrozenSuite(args.suite)
    directory=new_run('isolation-verification')
    summary={'provenance':'synthetic_fixture','suite':suite.identity(),'tests':{},'fixtures':{},'passed':False}
    try:
        for name in ('tests','integration_tests'):
            result=execute([sys.executable,'-m','unittest','discover','-s',name,'-v'],cwd=ROOT,timeout=180,
                           env_extra={'HOME':str(Path.home())})
            save_json(directory/(name+'.json'),result)
            summary['tests'][name]=result['exit_code']==0 and not result['timed_out']
            if not summary['tests'][name]:
                raise RuntimeError(result['stderr'])
        tester=TestsuiteAgent(EnvironmentAgent(60,ContainerExecutor()))
        for task in ('levenshtein','normalized','jaro_winkler'):
            rows=suite.cases(task,'visible')+suite.cases(task,'holdout')
            reference=suite.reference(task,'visible')+suite.reference(task,'holdout')
            result=tester.evaluate(ROOT/f'fixtures/{task}.py',rows,reference,('cpython','graal'),directory/task)
            summary['fixtures'][task]={key:result[key] for key in ('passed','total','all_pass')}
        summary['passed']=all(r['all_pass'] for r in summary['fixtures'].values())
    except Exception as exc:
        summary['error']={'type':type(exc).__name__,'message':str(exc)}
    finally:
        save_json(directory/'summary.json',summary)
        print(f'Archived: {archive_run(directory)}')
        print(json.dumps(summary,indent=2))
    return 0 if summary['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
