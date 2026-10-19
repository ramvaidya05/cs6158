"""E-Agent: reproducible execution, capability checks, and evidence collection."""
import ast
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from .process import execute
from .build import verify_build
from .storage import ROOT, save_json


class EnvironmentAgent:
    def __init__(self, timeout=60):
        self.timeout = timeout

    def java_command(self):
        verify_build()
        cp = ROOT / "java/target/classpath.txt"
        if not cp.exists() or not (ROOT / "java/target/classes/lab/Harness.class").exists():
            raise RuntimeError("Java harness not built. Run: python3 scripts/bootstrap.py")
        return ["java", "--enable-native-access=ALL-UNNAMED", "-Xmx768m",
                "-Dpolyglot.engine.userResourceCache=" + str(ROOT / ".cache/graalvm"), "-cp",
                str(ROOT / "java/target/classes") + os.pathsep + cp.read_text().strip(), "lab.Harness"]

    def doctor(self):
        version = execute(["java", "-version"], timeout=10) if shutil.which("java") else None
        return {"python": sys.version, "python_executable": sys.executable,
                "platform": platform.platform(), "machine": platform.machine(),
                "java": version, "maven_on_path": shutil.which("mvn"),
                "local_maven": (ROOT / ".tools/apache-maven-3.9.9/bin/mvn").exists(),
                "java_harness_built": (ROOT / "java/target/classpath.txt").exists(),
                "docker_on_path": shutil.which("docker"),
                "openai_api_key_configured": bool(os.environ.get("OPENAI_API_KEY")),
                "isolation": "local subprocess; not an OS sandbox",
                "graalpy_version": "25.0.0"}

    def run(self, mode, cases, artifact: Path, candidate=None):
        artifact.mkdir(parents=True, exist_ok=True)
        save_json(artifact / "inputs.json", cases)
        if not cases:
            raise ValueError("Refusing zero-test run")
        if candidate is not None:
            try:
                tree = ast.parse(candidate.read_text(encoding="utf-8"), filename="candidate.py")
                if not any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in tree.body):
                    raise SyntaxError("Candidate must define top-level function run")
            except (SyntaxError, UnicodeError) as exc:
                result = {"status": "syntax_error", "rows": [], "detail": str(exc)}
                save_json(artifact / "execution.json", result)
                return result
        if mode == "reference":
            command = self.java_command() + ["reference"]
        elif mode == "graal":
            command = self.java_command() + ["graal", str(candidate.resolve())]
        elif mode == "cpython":
            command = [sys.executable, "-I", str(ROOT / "migration_lab/worker.py"), str(candidate.resolve())]
        else:
            raise ValueError("Unknown execution mode")
        proc = execute(command, data=json.dumps(cases, ensure_ascii=True), timeout=self.timeout)
        rows = []
        detail = ""
        if proc["timed_out"]:
            status = "timeout"
        elif proc["exit_code"] != 0:
            status = "execution_error"
        elif proc["output_truncated"]:
            status = "protocol_error"
            detail = "Runner output exceeded capture limit"
        else:
            try:
                rows = json.loads(proc["stdout"])
                if not isinstance(rows, list) or len(rows) != len(cases):
                    raise ValueError("Missing or extra result rows")
                if [r["id"] for r in rows] != [c["id"] for c in cases]:
                    raise ValueError("Wrong case IDs/order")
                for r in rows:
                    if r.get("status") not in ("ok", "exception"):
                        raise ValueError("Unknown row status")
                status = "completed"
            except (ValueError, KeyError, TypeError) as exc:
                status, detail, rows = "protocol_error", str(exc), []
        result = {"status": status, "rows": rows, "detail": detail, "process": proc}
        save_json(artifact / "execution.json", result)
        return result
