"""Bind compiled Java artifacts to the exact source inputs used by bootstrap."""
import json
from .storage import ROOT, sha256, save_json


def source_fingerprint():
    paths = [ROOT / "java/pom.xml"]
    paths += list((ROOT / "java/src").rglob("*.java"))
    paths += list((ROOT / "vendor").rglob("*.java"))
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(paths)}


def record_build():
    paths = list((ROOT / "java/target/classes").rglob("*.class"))
    paths += [ROOT / "java/target/classpath.txt"]
    result = {"sources": source_fingerprint(), "artifacts": {
        str(p.relative_to(ROOT)): sha256(p) for p in sorted(paths)}}
    save_json(ROOT / "java/target/build.json", result)
    return result


def verify_build():
    manifest = ROOT / "java/target/build.json"
    if not manifest.exists():
        raise RuntimeError("Build manifest missing. Run: python3 scripts/bootstrap.py")
    result = json.loads(manifest.read_text())
    if result["sources"] != source_fingerprint():
        raise RuntimeError("Java source/POM changed since build. Run: python3 scripts/bootstrap.py")
    for name, digest in result["artifacts"].items():
        path = ROOT / name
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError("Compiled Java artifacts changed. Run: python3 scripts/bootstrap.py")
    return result
