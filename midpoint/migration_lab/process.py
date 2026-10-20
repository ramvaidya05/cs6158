"""Bounded pipe capture. Local processes still are not a security sandbox."""
import os
import selectors
import signal
import subprocess
import tempfile
import time


def execute(command, *, data="", timeout=60, cwd=None, env_extra=None, output_limit=2_000_000):
    allowed = ("PATH", "JAVA_HOME", "SYSTEMROOT", "WINDIR", "TMPDIR")
    env = {k: os.environ[k] for k in allowed if k in os.environ}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
               LANG="C.UTF-8", LC_ALL="C.UTF-8", TZ="UTC")
    env.update(env_extra or {})  # Trusted launcher settings, never candidate-supplied.
    started = time.monotonic()
    timed_out = truncated = False
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    with tempfile.TemporaryDirectory(prefix="migration-process-") as temporary:
        process = subprocess.Popen([str(x) for x in command], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   cwd=cwd or temporary, env=env, start_new_session=True)
        def kill_group():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            pending = memoryview(data.encode("utf-8"))
            with selectors.DefaultSelector() as selector:
                for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
                if pending:
                    os.set_blocking(process.stdin.fileno(), False)
                    selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
                else:
                    process.stdin.close()
                while selector.get_map():
                    remaining = timeout - (time.monotonic() - started)
                    if remaining <= 0:
                        timed_out = True
                        break
                    for key, _ in selector.select(min(remaining, 0.1)):
                        if key.data == "stdin":
                            try:
                                pending = pending[os.write(key.fd, pending[:65536]):]
                            except BrokenPipeError:
                                pending = memoryview(b"")
                            if not pending:
                                selector.unregister(key.fileobj)
                                key.fileobj.close()
                        else:
                            chunk = os.read(key.fd, 65536)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                continue
                            buffer = captured[key.data]
                            space = output_limit - len(buffer)
                            buffer.extend(chunk[:space])
                            if len(chunk) > space:
                                truncated = True
                    if truncated:
                        break
            if timed_out or truncated:
                kill_group()
            try:
                process.wait(timeout=max(0.01, timeout - (time.monotonic() - started)))
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_group()
                process.wait()
        finally:
            kill_group()
            process.wait()
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
    return {"command": [str(x) for x in command], "exit_code": process.returncode,
            "timed_out": timed_out, "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout": captured["stdout"].decode("utf-8", errors="replace"),
            "stderr": captured["stderr"].decode("utf-8", errors="replace"),
            "output_truncated": truncated}
