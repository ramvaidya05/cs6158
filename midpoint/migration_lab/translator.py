"""M-Agent: bounded context assembly; no filesystem/tool access is given to the model."""
import json
from .benchmark import SOURCES, SOURCE_DIR
from .storage import ROOT


class MigrationAgent:
    def __init__(self, backend):
        self.backend = backend

    def prompt(self, task, previous=None, feedback=None):
        if task == "commons_cli":
            from .cli_task import prompt
            blocks = [prompt()]
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
    def feedback(summary):
        return {mode: {"passed": r["passed"], "total": r["total"], "status": r["status"],
                       "failures": r["failures"][:6]}
                for mode, r in summary["runtimes"].items()}
