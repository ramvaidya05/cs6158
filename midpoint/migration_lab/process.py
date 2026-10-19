"""Bounded subprocess execution. A local process is not a security sandbox."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def execute(command, *, data="", timeout=60, cwd=None):
    allowed = ("PATH", "JAVA_HOME", "SYSTEMROOT", "WINDIR", "TMPDIR")
    env = {k: os.environ[k] for k in allowed if k in os.environ}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    env.update(LANG="C.UTF-8", LC_ALL="C.UTF-8", TZ="UTC")
    started = time.monotonic()
    timed_out = False
    with tempfile.TemporaryDirectory(prefix="migration-process-") as temporary:
        with open(Path(temporary) / "stdout", "w+b") as out, open(Path(temporary) / "stderr", "w+b") as err:
            process = subprocess.Popen([str(x) for x in command], stdin=subprocess.PIPE,
                                       stdout=out, stderr=err, cwd=cwd or temporary,
                                       env=env, start_new_session=True)
            try:
                process.communicate(data.encode("utf-8"), timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            out.seek(0)
            err.seek(0)
            limit = 2_000_000
            stdout = out.read(limit + 1)
            stderr = err.read(limit + 1)
    return {"command": [str(x) for x in command], "exit_code": process.returncode,
            "timed_out": timed_out, "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout": stdout[:limit].decode("utf-8", errors="replace"),
            "stderr": stderr[:limit].decode("utf-8", errors="replace"),
            "output_truncated": len(stdout) > limit or len(stderr) > limit}
