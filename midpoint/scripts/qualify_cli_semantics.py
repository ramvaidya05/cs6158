"""Synthetic mutation qualification on visible cases only; Java is the oracle."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from migration_lab.protocol import FrozenSuite
from migration_lab.environment import EnvironmentAgent
from migration_lab.isolation import ContainerExecutor
from migration_lab.evaluation import TestsuiteAgent
from migration_lab.storage import new_run,save_json,sha256
from migration_lab.experiments import archive_run

MUTATIONS={
'alias_lost':'''import copy
_old = Options.addOption
def _bad(self, option):
    _old(self, option)
    return copy.copy(self)
Options.addOption = _bad''',
'parser_state_leak':'''_old = DefaultParser.parse
def _bad(self, *args):
    if hasattr(self, '_previous'): return self._previous
    self._previous = _old(self, *args)
    return self._previous
DefaultParser.parse = _bad''',
'missing_value_empty_string':'''_old = CommandLine.getOptionValue
def _bad(self, *args):
    value = _old(self, *args)
    return '' if value is None else value
CommandLine.getOptionValue = _bad''',
'wrong_exception_type':'''_old = DefaultParser.parse
def _bad(self, *args):
    try: return _old(self, *args)
    except Exception: raise ValueError('incorrect exception mapping')
DefaultParser.parse = _bad''',
'reversed_values':'''_old = CommandLine.getOptionValues
def _bad(self, *args):
    values = _old(self, *args)
    return list(reversed(values)) if values else values
CommandLine.getOptionValues = _bad''',
'partial_matching_disabled':'''_old = DefaultParser.__init__
def _bad(self, allow_partial): _old(self, False)
DefaultParser.__init__ = _bad''',
'required_ignored':'''def _bad(self, required): pass
Option.setRequired = _bad''',
'option_replacement_ignored':'''_old = Options.addOption
def _bad(self, option):
    if self.hasOption(option.getOpt()): return self
    return _old(self, option)
Options.addOption = _bad'''
}

EXTENDED_MUTATIONS = {
    'group_required_ignored': 'OptionGroup.setRequired = lambda self, value: None',
    'group_selection_lost': 'OptionGroup.getSelected = lambda self: None',
    'group_members_lost': 'OptionGroup.getNames = lambda self: []',
    'group_conflict_ignored': 'OptionGroup.setSelected = lambda self, option: setattr(self, "selected", option.getKey() if option else None)',
    'description_update_lost': 'Option.setDescription = lambda self, value: None',
    'arg_name_update_lost': 'Option.setArgName = lambda self, value: None',
    'arity_update_lost': 'Option.setArgs = lambda self, value: None',
    'optional_update_lost': 'Option.setOptionalArg = lambda self, value: None',
}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--suite',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);args=p.parse_args()
    suite=FrozenSuite(args.suite);rows=suite.cases('commons_cli','visible');refs=suite.reference('commons_cli','visible')
    folder=new_run('cli-semantic-qualification');print(folder,flush=True)
    tester=TestsuiteAgent(EnvironmentAgent(90,ContainerExecutor()))
    baseline=folder/'baseline.py';baseline.write_text(args.baseline.read_text())
    result=tester.evaluate(baseline,rows,refs,('cpython','graal'),folder/'baseline')
    summary={'provenance':'synthetic_mutation','suite':suite.identity(),'baseline_sha256':sha256(baseline),'baseline_source':str(args.baseline),'baseline':{k:result[k] for k in ('passed','total','all_pass')},'policy':'Only newly failing baseline-passing visible cases count; infrastructure failure is not semantic detection; holdout excluded','mutations':{}}
    mutations = {**MUTATIONS, **EXTENDED_MUTATIONS} if suite.identity()["profile"] == "commons-cli-extended-v3" else MUTATIONS
    for name,patch in mutations.items():
        candidate=folder/(name+'.py');candidate.write_text(baseline.read_text()+'\n'+patch+'\n')
        observed=tester.evaluate(candidate,rows,refs,('cpython','graal'),folder/name)
        modes={}
        for mode in ('cpython','graal'):
            old=result['runtimes'][mode];new=observed['runtimes'][mode]
            lost=sorted(set(old['passed_ids'])-set(new['passed_ids'])) if new['status']=='completed' and old['status']=='completed' else []
            modes[mode]={'status':new['status'],'newly_failing_case_ids':lost,'detected':bool(lost)}
        summary['mutations'][name]=modes
        print(name,{m:r['detected'] for m,r in modes.items()},flush=True)
    summary['detected_in_both']=sum(all(v['detected'] for v in r.values()) for r in summary['mutations'].values());summary['total_mutants']=len(mutations)
    save_json(folder/'summary.json',summary);print('Archived:',archive_run(folder));print(json.dumps(summary,indent=2))
    return 0 if summary['detected_in_both']==len(mutations) else 1
if __name__=='__main__':raise SystemExit(main())
