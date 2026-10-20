"""Disposable, resource-limited Docker execution with no host repository mount."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid
from .process import execute
from .storage import ROOT, sha256


class IsolationError(RuntimeError):
    pass


def docker(args, **kwargs):
    # The trusted CLI needs its context/socket configuration. It is never forwarded
    # into a candidate container; only the explicit --env values below enter it.
    return execute(["docker", *args], env_extra={"HOME": str(Path.home())}, **kwargs)


class ContainerExecutor:
    isolated = True

    def __init__(self, lock_path=None, fault="none"):
        if fault not in ("none", "graal-cache"):
            raise ValueError("Unknown controlled environment fault")
        self.lock_path = lock_path or ROOT / ".cache/container-images.json"
        self.lock = json.loads(self.lock_path.read_text())
        for name, digest in self.lock["inputs"].items():
            if sha256(ROOT / name) != digest:
                raise IsolationError("Container inputs changed; rebuild with scripts/build_containers.py")
        self.cache_path = "/unwritable/graalvm" if fault == "graal-cache" else "/tmp/graalvm"
        self.fault = fault
        self.verified = set()

    def identity(self):
        return {"backend": "docker", "images": self.lock["images"],
                "network": "none", "read_only": True, "user": "65532:65532",
                "cpus": 1, "memory_mb": {"cpython": 256, "graal": 1536},
                "pids": 128, "tmpfs_mb": {"cpython": 64, "graal": 512},
                "output_bytes_per_stream": 2_000_000, "fault": self.fault,
                "graal_cache": self.cache_path}

    def verify(self, mode):
        if mode in self.verified:
            return
        expected = self.lock["images"][mode]["id"]
        result = docker(["image", "inspect", expected, "--format", "{{.Id}}"], timeout=15)
        if result["exit_code"] != 0 or result["stdout"].strip() != expected:
            raise IsolationError("Pinned container image/daemon unavailable; no local fallback")
        self.verified.add(mode)

    def command(self, mode, candidate, name):
        image = self.lock["images"][mode]["id"]
        memory = "256m" if mode == "cpython" else "1536m"
        tmp = "64m" if mode == "cpython" else "512m"
        # GraalPy extracts native libraries into its ephemeral cache, requiring exec.
        tmp_flags = "noexec," if mode == "cpython" else "exec,"
        command = ["run", "--name", name, "--pull=never", "--interactive",
                   "--network=none", "--read-only", "--user=65532:65532",
                   "--cap-drop=ALL", "--security-opt=no-new-privileges",
                   "--cpus=1", "--memory=" + memory, "--memory-swap=" + memory,
                   "--pids-limit=128", "--ulimit=nofile=256:256", "--ipc=none",
                   "--log-driver=none", "--workdir=/tmp",
                   "--tmpfs=/tmp:rw,nosuid,nodev," + tmp_flags + "size=" + tmp + ",mode=1777",
                   "--env=HOME=/tmp", "--env=LANG=C.UTF-8", "--env=LC_ALL=C.UTF-8",
                   "--env=TZ=UTC", "--env=PYTHONDONTWRITEBYTECODE=1",
                   "--mount", f"type=bind,src={candidate},dst=/candidate.py,readonly"]
        if mode == "cpython":
            return command + [image, "/candidate.py"]
        return command + [image, "--enable-native-access=ALL-UNNAMED", "-Xmx768m",
                          "-Dpolyglot.engine.userResourceCache=" + self.cache_path,
                          "-cp", "/runner/classes:/runner/jars/*", "lab.GuestHarness", "/candidate.py"]

    def run(self, mode, candidate, data, timeout):
        self.verify(mode)
        name = "migration-" + uuid.uuid4().hex
        # A single copied source file is mounted, not its parent (which holds prompts/results).
        with tempfile.TemporaryDirectory(prefix="migration-candidate-") as tmp:
            source = Path(tmp) / "candidate.py"
            shutil.copyfile(candidate, source)
            source.chmod(0o444)
            command = self.command(mode, source, name)
            try:
                result = docker(command, data=data, timeout=timeout)
                inspect = docker(["inspect", name, "--format", "{{json .State}}"], timeout=10)
                if inspect["exit_code"] == 0:
                    result["container_state"] = json.loads(inspect["stdout"])
                result["isolation"] = self.identity()
                return result
            finally:
                cleanup = docker(["rm", "--force", name], timeout=15)
                if cleanup["exit_code"] != 0 and "No such container" not in cleanup["stderr"]:
                    raise IsolationError("Container cleanup failed; stop before further candidates")

    def remediate(self, mode, result):
        """One allowlisted configuration repair, based only on a trusted probe."""
        stderr = result.get("process", {}).get("stderr", "")
        denied = any(s in stderr for s in ("Read-only file system", "Permission denied", "AccessDeniedException"))
        if mode == "graal" and self.cache_path == "/unwritable/graalvm" and denied:
            before = self.identity()
            self.cache_path = "/tmp/graalvm"
            return {"action": "use_ephemeral_graal_cache", "before": before,
                    "after": self.identity(), "reason": "Trusted preflight reports cache write denial"}
        return None
