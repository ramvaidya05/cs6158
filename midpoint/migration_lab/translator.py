"""M-Agent: bounded context assembly; no filesystem/tool access is given to the model."""
import json
from .benchmark import SOURCES, SOURCE_DIR
from .storage import ROOT


class MigrationAgent:
    def __init__(self, backend, *, compact_cli=False):
        self.backend = backend
        self.compact_cli = compact_cli

    def prompt(self, task, previous=None, feedback=None):
        if task == "commons_csv":
            from .csv_task import prompt
            blocks = [prompt()]
        elif task == "commons_cli":
            from .cli_task import prompt
            blocks = [prompt(compact=self.compact_cli)]
        else:
            blocks = [f"Translate task: {task}. Output only the requested JSON schema."]
            for name in ("translation_contract.md", "java_python_semantics.md"):
                blocks.append(f"VERIFIED CONTEXT: {name}\n" + (ROOT / "knowledge" / name).read_text())
            for name in SOURCES[task]:
                blocks.append(f"JAVA SOURCE: {name}\n" + (SOURCE_DIR / name).read_text())
            for path in sorted((SOURCE_DIR / "interfaces").glob("*.java")):
                blocks.append(f"JAVA INTERFACE: {path.name}\n" + path.read_text())
        if previous is not None:
            blocks.append("PREVIOUS CANDIDATE:\n" + previous)
            blocks.append("VISIBLE EXECUTION FEEDBACK (repair the general behavior, not specific examples):\n" +
                          json.dumps(feedback, ensure_ascii=True))
        return "\n\n".join(blocks)

    @staticmethod
    def feedback(summary, mode="full"):
        if mode not in ("full", "basic", "operation", "pruned"):
            raise ValueError("Unknown feedback mode")
        if mode == "pruned":
            from .retry_memory import diagnostics
            return diagnostics(summary)
        if mode == "basic":
            return {runtime: {k:r[k] for k in ("passed", "total", "status")} for runtime,r in summary["runtimes"].items()}
        if mode == "operation":
            result = {}
            for runtime,r in summary["runtimes"].items():
                failures = []
                for f in r["failures"][:6]:
                    diff = f.get("first_difference")
                    if diff is not None:
                        failures.append({"case_id": f["case"]["id"], "operations": f["case"]["operations"][:diff["step"]+1], "first_difference": diff})
                    else:
                        failures.append(f)
                result[runtime] = {**{k:r[k] for k in ("passed", "total", "status")}, "failures":failures}
            return result
        return {mode: {"passed": r["passed"], "total": r["total"], "status": r["status"],
                       "failures": r["failures"][:6]}
                for mode, r in summary["runtimes"].items()}
