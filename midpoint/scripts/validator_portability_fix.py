"""Deterministic assisted remediation, distinct from a successful model repair."""
import ast
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from migration_lab.storage import ROOT, new_run, save_json, sha256
from migration_lab.reporting import verify_archive
from migration_lab.environment import EnvironmentAgent
from migration_lab.isolation import ContainerExecutor
from migration_lab.experiments import archive_run
from scripts.validator_luhn_pilot import score
from scripts.validator_runtime_repair import PARENT, accepts

CONTINUATION = ROOT / 'evidence/20261121T233614Z-validator-runtime-repair-d8f3e047'


def remediate(source, diagnosis):
    """Only replace one-argument unicodedata.decimal calls under verified diagnosis."""
    if diagnosis['runtimes']['graal']['decimal']['callable']:
        raise ValueError('Remediation requires confirmed missing decimal API')
    if diagnosis['java_char_values_verified'] != 65536:
        raise ValueError('Unverified Java mapping')
    tree = ast.parse(source)
    if any(isinstance(n, ast.Name) and n.id == '_java_decimal_portable' for n in ast.walk(tree)):
        raise ValueError('Helper name collision')
    class Rewrite(ast.NodeTransformer):
        changed = 0
        def visit_Call(self, node):
            self.generic_visit(node)
            f = node.func
            if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                    and f.value.id == 'unicodedata' and f.attr == 'decimal'):
                if len(node.args) != 1 or node.keywords:
                    raise ValueError('Unsupported decimal call signature')
                node.func = ast.Name(id='_java_decimal_portable', ctx=ast.Load())
                self.changed += 1
            return node
    rewrite = Rewrite()
    tree = rewrite.visit(tree)
    if rewrite.changed != 1:
        raise ValueError('Expected exactly one eligible call')
    helper = '''def _java_decimal_portable(character):
    value = ord(character)
    for base in BASES:
        if base <= value < base + 10:
            return value - base
    raise ValueError("Not a Java decimal char")
'''.replace('BASES', repr(tuple(diagnosis['java_decimal_bases'])))
    return '# Deterministic assisted portability repair; original model candidate archived.\n' + helper + '\n' + ast.unparse(ast.fix_missing_locations(tree)) + '\n'


def main():
    verify_archive(CONTINUATION)
    verify_archive(PARENT)
    directory = new_run('validator-assisted-qualification')
    diagnosis = json.loads((CONTINUATION / 'diagnosis/diagnosis.json').read_text())
    candidate = directory / 'candidate.py'
    candidate.write_text(remediate((CONTINUATION / 'candidate.py').read_text(), diagnosis))
    suite = json.loads((PARENT / 'frozen-suite.json').read_text())
    environment = EnvironmentAgent(60, ContainerExecutor())
    result = {'provenance': 'deterministic developer-assisted API substitution; not model repair success',
              'model_calls': 0, 'parent': CONTINUATION.name,
              'candidate_sha256': sha256(candidate), 'scores': {}}
    for split in ('visible', 'holdout'):
        result['scores'][split] = score(environment, candidate, suite['cases'][split], suite['reference'][split], split, directory)
    baseline = json.loads((PARENT / 'attempt-0/visible/score.json').read_text())
    result['accepted'] = accepts(baseline, result['scores']['visible'])
    result['passed'] = all(v['passed'] == v['total'] for split in result['scores'].values() for v in split.values())
    save_json(directory / 'summary.json', result)
    print('Archive:', archive_run(directory))
    print('All API cases passed:', result['passed'])
    if result['passed'] and result['accepted']:
        (ROOT / 'translations/commons_validator_luhn.py').write_text(candidate.read_text())
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
