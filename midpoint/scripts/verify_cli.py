"""Qualify stateful adapters and bounded repair using trusted fixtures only."""
import argparse
import json
from pathlib import Path
import shutil
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.backends import ReplayBackend
from migration_lab.build import verify_build
from migration_lab.controller import run_task
from migration_lab.protocol import freeze
from migration_lab.storage import new_run, save_json, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true')
    args = parser.parse_args()
    verify_build()
    directory = new_run('commons-cli-qualification')
    print('Artifacts: ' + str(directory), flush=True)
    suite = freeze(directory / 'suite.json', seed=6158, tasks=('commons_cli',))
    _, result = run_task('commons_cli', ReplayBackend(ROOT/'fixtures/replay.json'),
                         suite=suite, directory=directory/'replay', timeout=90)
    if not result['validated'] or len(result['attempts']) != 2 or result['baseline_visible']['all_pass']:
        raise RuntimeError('Expected planted state bug rejection and successful repaired fixture')
    summary = {'provenance':'synthetic_fixture',
               'interpretation':'Adapter/controller qualification, not model translation accuracy',
               'scope':'Commons CLI 1.9.0 four-class API slice; authored scenarios, not upstream CLI JUnit',
               'holdout_limitation':'New names/values using the same 20 scenario templates; not independent semantic coverage',
               'suite':suite.identity(), 'attempts':len(result['attempts']), 'validated':result['validated']}
    for key in ('baseline_visible','selected_visible','baseline_holdout','selected_holdout'):
        summary[key] = {k:result[key][k] for k in ('passed','total','all_pass')}
    save_json(directory/'summary.json',summary)
    if args.archive:
        destination=ROOT/'evidence'/directory.name
        shutil.copytree(directory,destination)
        save_json(destination/'checksums.json',{str(p.relative_to(destination)):sha256(p) for p in sorted(destination.rglob('*')) if p.is_file()})
        print('Archived: '+str(destination))
    print(json.dumps(summary,indent=2))
    return 0

if __name__ == '__main__': raise SystemExit(main())
