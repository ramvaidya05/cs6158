"""Prepare explicitly synthetic v3 harness fixtures from an archived Gemini response.

The source model response is unchanged; additions below are hand-written adapters
for qualification, never counted as new model translations or accuracy results.
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'evidence/20261117T204352Z-experiment-1f46722d/trial-000/commons_cli/one_shot/final.py'
PATCH = '''
# Synthetic qualification additions (not model output).
def _get_description(self): return self.description
def _set_description(self, value): self.description = value
def _get_arg_name(self): return self.argName
def _set_arg_name(self, value): self.argName = value
def _set_optional(self, value): self.optionalArg = value
def _set_args(self, value): self.argCount = value
def _required(self): return list(self.requiredOpts)
Option.getDescription = _get_description
Option.setDescription = _set_description
Option.getArgName = _get_arg_name
Option.setArgName = _set_arg_name
Option.setOptionalArg = _set_optional
Option.setArgs = _set_args
Options.getRequiredOptions = _required
'''

def main():
    import argparse, hashlib
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    source=SOURCE.read_text()+PATCH
    (a.output/'good.py').write_text(source)
    (a.output/'partial.py').write_text(source+'\nOption.getDescription = lambda self: "incorrect"\n')
    (a.output/'bad.py').write_text(source+'\nOption.getDescription = lambda self: "incorrect"\nOptionGroup.isRequired = lambda self: False\n')
    (a.output/'replay.json').write_text(json.dumps({'provenance':'synthetic_fixture','tasks':{'commons_cli':['bad.py','partial.py','good.py']},
        'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'note':'Hand-written additions and mutations; not fresh inference.'},indent=2)+'\n')
if __name__=='__main__':main()
