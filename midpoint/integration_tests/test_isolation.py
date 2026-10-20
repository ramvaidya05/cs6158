"""Explicit Docker integration tests; run before live generation, never silently skip."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from migration_lab.environment import EnvironmentAgent
from migration_lab.isolation import ContainerExecutor, IsolationError
from migration_lab.benchmark import cases
from migration_lab.storage import ROOT, sha256


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.env = EnvironmentAgent(30, ContainerExecutor())

    def run_code(self, code, mode='cpython', timeout=30):
        p = self.path/'candidate.py'
        p.write_text(code)
        self.env.timeout = timeout
        return self.env.run(mode, cases('levenshtein')[:1],self.path/'artifacts',p)

    def value(self, code, mode='cpython'):
        result = self.run_code(code, mode)
        self.assertEqual(result['status'],'completed',str(result)[-2000:])
        return result['rows'][0].get('value')

    def test_host_secret_and_repository_absent(self):
        canary = self.path/'host-secret'
        canary.write_text('secret-canary')
        code = f'''import os
from pathlib import Path
def run(*args):
    assert 'OPENAI_API_KEY' not in os.environ
    assert not Path({str(canary)!r}).exists()
    assert not Path({str(ROOT)!r}).exists()
    assert not Path('/var/run/docker.sock').exists()
    assert not Path('/runner/classes/info').exists()
    return 1
'''
        with patch.dict(os.environ, OPENAI_API_KEY='credential-sentinel'):
            self.assertEqual(self.value(code),1)

    def test_runner_and_candidate_read_only(self):
        before=sha256(ROOT/'migration_lab/worker.py')
        self.assertEqual(self.value('''def run(*args):
    denied=0
    for path in ('/runner/worker.py','/candidate.py','/new-file'):
        try:
            with open(path,'w') as f: f.write('tamper')
        except OSError: denied+=1
    return denied
'''),3)
        self.assertEqual(sha256(ROOT/'migration_lab/worker.py'),before)

    def test_external_network_denied(self):
        self.assertEqual(self.value('''import socket
def run(*args):
    try:
        socket.create_connection(('1.1.1.1',443),timeout=1).close()
        return 0
    except OSError: return 1
'''),1)

    def test_cpu_and_pid_limits_enforced(self):
        self.assertEqual(self.value('''from pathlib import Path
def run(*args):
    quota, period = map(int,Path('/sys/fs/cgroup/cpu.max').read_text().split())
    assert quota/period == 1
    assert int(Path('/sys/fs/cgroup/pids.max').read_text()) == 128
    assert int(Path('/sys/fs/cgroup/memory.max').read_text()) == 256*1024*1024
    return 1
'''),1)

    def test_process_creation_is_bounded(self):
        self.assertEqual(self.value('''import subprocess
def run(*args):
    children=[]
    try:
        for i in range(160): children.append(subprocess.Popen(['sleep','10']))
    except OSError: return 1
    finally:
        for child in children: child.terminate()
        for child in children: child.wait()
    return 0
'''),1)

    def test_memory_limit(self):
        result=self.run_code('def run(*args):\n    x=bytearray(1024*1024*1024)\n    return len(x)\n')
        self.assertEqual(result['status'],'memory_limit')

    def test_disk_limit(self):
        self.assertEqual(self.value('''def run(*args):
    try:
        with open('/tmp/fill','wb') as f:
            for i in range(100): f.write(b'x'*(1024*1024))
    except OSError: return 1
    return 0
'''),1)

    def test_time_and_output_limits(self):
        self.assertEqual(self.run_code('def run(*args):\n    while True: pass\n',timeout=2)['status'],'timeout')
        self.assertEqual(self.run_code('def run(*args):\n    while True: print("x"*10000)\n')['status'],'output_limit')

    def test_graal_host_file_and_network_denied(self):
        self.assertEqual(self.value('''def run(*args):
    try:
        open('/etc/passwd').read()
    except Exception: return 1
    return 0
''','graal'),1)
        result = self.run_code('''def run(*args):
    import socket
    socket.create_connection(('1.1.1.1',443),timeout=1)
    return 0
''','graal')
        self.assertEqual(result['status'], 'execution_error')
        self.assertIn('getaddrinfo was excluded', result['process']['stderr'])

    def test_missing_image_fails_closed(self):
        self.env.executor.lock['images']['cpython']['id']='sha256:'+'0'*64
        with self.assertRaises(IsolationError):
            self.run_code('def run(*args): return 0')

    def test_trusted_cache_diagnosis_and_bounded_remediation(self):
        self.env=EnvironmentAgent(60,ContainerExecutor(fault='graal-cache'))
        result=self.env.run('graal',cases('levenshtein')[:1],self.path/'failed',ROOT/'fixtures/preflight.py')
        self.assertNotEqual(result['status'],'completed')
        action=self.env.remediate('graal',result)
        self.assertIsNotNone(action, str(result)[-4000:])
        result=self.env.run('graal',cases('levenshtein')[:1],self.path/'repaired',ROOT/'fixtures/preflight.py')
        self.assertEqual(result['status'],'completed')
        self.assertIsNone(self.env.remediate('graal',result))
