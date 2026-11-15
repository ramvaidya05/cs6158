"""Trusted dispatch; python -I is import isolation, not an OS sandbox."""
import contextlib
from pathlib import Path
import sys

def main():
    folder = Path(__file__).resolve().parent
    manifest = folder / "commons_cli.json"
    if not manifest.exists():
        manifest = folder.parent / "benchmarks/commons_cli.json"
    scope = {"_source": Path(sys.argv[1]).read_text(encoding="utf-8"),
             "_cases_json": sys.stdin.read(), "_contract_json": manifest.read_text()}
    with contextlib.redirect_stdout(sys.stderr):
        exec(compile((folder / "scenarios.py").read_text(), "scenarios.py", "exec"), scope)
        exec(compile((folder / "guest_driver.py").read_text(), "guest_driver.py", "exec"), scope)
    print(scope["_result_json"])

if __name__ == "__main__":
    main()
