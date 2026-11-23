"""Trusted, bounded Unicode capability diagnosis; never reads evaluation cases."""
import json
from .process import execute
from .storage import save_json

PROBE = '''import json
import unicodedata
def run(operation, data):
    report = {}
    for name in ("category", "decimal", "digit"):
        method = getattr(unicodedata, name, None)
        entry = {"callable": callable(method)}
        if callable(method):
            try:
                entry["sample"] = method("1")
            except Exception as exc:
                entry["error"] = type(exc).__name__
        report[name] = entry
    return json.dumps(report, sort_keys=True)
'''

JAVA = '''class DecimalContract {
 public static void main(String[] args) {
  for (int i=0;i<65536;i++) {
   char c=(char)i;
   int n=Character.isDigit(c)?Character.getNumericValue(c):-1;
   System.out.print((char)(66+n));
  }
 }
}'''


def decimal_bases(mapping):
    if len(mapping) != 65536:
        raise ValueError("Incomplete Java char domain")
    bases = [i for i, value in enumerate(mapping) if value == 'B']
    expected = [-1] * 65536
    for base in bases:
        if base + 9 >= 65536:
            raise ValueError("Invalid decimal block")
        for offset in range(10):
            expected[base + offset] = offset
    if any(ord(value) - 66 != expected[i] for i, value in enumerate(mapping)):
        raise ValueError("Java decimal digits cannot be represented as ten-digit blocks")
    return bases


def diagnose(environment, directory):
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / 'capability-probe.py'
    candidate.write_text(PROBE)
    cases = [{'id': 'unicode-capabilities', 'task': 'commons_validator_luhn',
              'operation': 'calculate', 'data': '1'}]
    result = {'runtimes': {}}
    for mode in ('cpython', 'graal'):
        observed = environment.run(mode, cases, directory / mode, candidate)
        if observed['status'] != 'completed' or len(observed['rows']) != 1 or observed['rows'][0].get('status') != 'ok':
            raise RuntimeError('Capability probe failed: ' + mode)
        result['runtimes'][mode] = json.loads(observed['rows'][0]['value'])
    source = directory / 'DecimalContract.java'
    source.write_text(JAVA)
    oracle = execute(environment.java_command()[:1] + [str(source.resolve())], timeout=30)
    save_json(directory / 'java-character-domain.json', oracle)
    if oracle['exit_code'] != 0:
        raise RuntimeError('Java decimal contract probe failed')
    result['java_decimal_bases'] = decimal_bases(oracle['stdout'])
    result['java_char_values_verified'] = 65536
    save_json(directory / 'diagnosis.json', result)
    return result
