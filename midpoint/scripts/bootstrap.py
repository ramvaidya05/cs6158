"""Install Maven locally, verify its published SHA-512, and build the harness."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.9.9"


def main():
    local = ROOT / ".tools" / f"apache-maven-{VERSION}" / "bin" / "mvn"
    mvn = os.environ.get("MAVEN_CMD") or shutil.which("mvn")
    if not mvn and not local.exists():
        target = ROOT / ".tools"
        target.mkdir(exist_ok=True)
        name = f"apache-maven-{VERSION}-bin.tar.gz"
        url = f"https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/{VERSION}/{name}"
        data = urllib.request.urlopen(url, timeout=60).read()
        expected = urllib.request.urlopen(url + ".sha512", timeout=30).read().decode().strip().split()[0]
        if hashlib.sha512(data).hexdigest() != expected:
            raise RuntimeError("Maven checksum mismatch")
        archive = target / name
        archive.write_bytes(data)
        with tarfile.open(archive) as tf:
            tf.extractall(target, filter="data")
    mvn = mvn or str(local)
    subprocess.run([mvn, "--batch-mode", "-U", "-Dmaven.repo.local=" + str(ROOT / ".cache/m2"),
                    "-f", str(ROOT / "java/pom.xml"), "test",
                    "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath",
                    "-Dmdep.outputFile=target/classpath.txt"], check=True, cwd=ROOT)
    sys.path.insert(0, str(ROOT))
    from migration_lab.build import record_build
    record_build()


if __name__ == "__main__":
    main()
