"""Build minimal candidate images from explicit inputs; never send the repo as context."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from migration_lab.build import verify_build
from migration_lab.storage import sha256, save_json


def main():
    verify_build()
    lock = {"schema": 1, "images": {}, "inputs": {}}
    sources = [ROOT / "migration_lab/worker.py", *sorted((ROOT / "containers").glob("*"))]
    jars = [Path(p) for p in (ROOT / "java/target/classpath.txt").read_text().strip().split(os.pathsep)]
    for path in sources + jars:
        lock["inputs"][str(path.relative_to(ROOT))] = sha256(path)
    for mode in ("cpython", "graal"):
        with tempfile.TemporaryDirectory(prefix="migration-image-") as tmp:
            context = Path(tmp)
            shutil.copy2(ROOT / f"containers/Dockerfile.{mode}", context / "Dockerfile")
            if mode == "cpython":
                shutil.copy2(ROOT / "migration_lab/worker.py", context / "worker.py")
            else:
                shutil.copy2(ROOT / "containers/GuestHarness.java", context / "GuestHarness.java")
                (context / "jars").mkdir()
                for i, jar in enumerate(jars):
                    shutil.copy2(jar, context / "jars" / f"{i:03}-{jar.name}")
            tag = f"migration-lab-{mode}:v1"
            subprocess.run(["docker", "build", "--network=none", "--tag", tag, str(context)], check=True)
            inspect = json.loads(subprocess.check_output(["docker", "image", "inspect", tag]))[0]
            lock["images"][mode] = {"id": inspect["Id"], "tag": tag,
                                    "architecture": inspect["Architecture"], "os": inspect["Os"]}
    save_json(ROOT / ".cache/container-images.json", lock)
    print(json.dumps(lock["images"], indent=2))


if __name__ == "__main__":
    main()
