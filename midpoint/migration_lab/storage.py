from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def new_run(label: str) -> Path:
    # Label originates from fixed CLI choices, not arbitrary paths.
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + label + "-" + uuid.uuid4().hex[:8]
    path = ROOT / "runs" / name
    path.mkdir(parents=True, exist_ok=False)
    return path


def protected_hashes():
    paths = []
    for directory in ("vendor", "java/src", "migration_lab", "knowledge", "benchmarks", "fixtures", "containers", "tests", "integration_tests", "scripts"):
        paths.extend(p for p in (ROOT / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts)
    paths.append(ROOT / "java/pom.xml")
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(paths)}
