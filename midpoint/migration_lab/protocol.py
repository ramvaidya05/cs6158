"""Evaluator-owned, frozen input sets. Never import these into prompt assembly."""
import json
import random
import secrets
from pathlib import Path
from .benchmark import TASKS, ALL_TASKS, cases, verify_vendor
from .environment import EnvironmentAgent
from .evaluation import TestsuiteAgent
from .storage import ROOT, save_json, sha256


def evaluation_cases(task, seed, count=100):
    rng = random.Random(seed)
    rows = []
    def add(a, b, operation="distance", parameter=None):
        rows.append({"id": f"{task}-evaluation-{len(rows):04}", "task": task, "a": a, "b": b,
                     "operation": operation, "parameter": parameter})
    # Explicit semantic strata supplement random inputs, including high-overlap
    # strings needed to exercise JaroWinkler's binary32 and prefix behavior.
    for a, b in [("", ""), (None, ""), ("", None), (None, None),
                 ("🚀", ""), ("😀", "😃"), ("a🚀b", "ab"), ("é", "e\u0301"),
                 ("\x00\r\n", "\n\x00"), ("a" * 64, "a" * 63 + "b"),
                 ("longcommonprefixABC", "longcommonprefixACB"), ("ab" * 40, "ba" * 40)]:
        add(a, b)
        if task != "levenshtein":
            add(a, b, "similarity")
    if task == "levenshtein":
        for limit in (-2147483648, -1, 0, 1, 2, 3, 2147483647):
            for a, b in (("abc", "xyz"), ("", "abc"), ("abc", "abc"), ("🚀a", "a")):
                add(a, b, parameter=limit)
    elif task == "jaro_winkler":
        for threshold in (-1.0, 0.0, 0.699999999, 0.7, 0.700000001, 1.0, 1.1):
            add("commonprefixabcdefgh", "commonprefixabcedfgh", "similarity", threshold)
    alphabet = "aAbB09 \t\n\x00é\u0301中🚀😀"
    for n in range(count):
        a = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 65)))
        if n % 2 and a:
            position = rng.randrange(len(a))
            b = a[:position] + rng.choice(alphabet) + a[position + 1:]
        else:
            b = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 65)))
        op = "distance" if task == "levenshtein" or n % 2 else "similarity"
        parameter = rng.choice([-1, 0, 1, 2, 8]) if task == "levenshtein" and n % 3 == 0 else None
        if task == "jaro_winkler" and n % 3 == 0:
            parameter = rng.choice([0.0, 0.7, 0.9, 1.0])
        add(a, b, op, parameter)
    return rows


def freeze(path, seed=None, tasks=TASKS):
    if not tasks or len(set(tasks)) != len(tasks) or any(t not in ALL_TASKS for t in tasks):
        raise ValueError("Unsupported or duplicate tasks")
    path = Path(path)
    if path.exists():
        raise ValueError("Refusing to overwrite a frozen evaluation suite")
    seed = seed if seed is not None else secrets.randbits(64)
    payload = {"schema": 1, "seed": seed, "source": verify_vendor(), "tasks": {},
               "comparator_sha256": sha256(ROOT / "migration_lab/evaluation.py"),
               "generator_sha256": sha256(Path(__file__)),
               "policy": "Evaluator only; all paired selections freeze before holdout scoring"}
    if tasks != TASKS:
        payload["schema"] = 2
        payload["task_identities"] = {}
        if "commons_cli" in tasks:
            from .cli_task import identity
            payload["task_identities"]["commons_cli"] = identity()
    tester = TestsuiteAgent(EnvironmentAgent())
    evidence = path.parent / (path.stem + "-oracle")
    for task in tasks:
        payload["tasks"][task] = {}
        for split, rows in (("visible", cases(task)), ("holdout", cases(task, "holdout", seed) if task == "commons_cli" else evaluation_cases(task, seed))):
            reference = tester.reference(rows, evidence / task / split)
            repeated = tester.reference(rows, evidence / task / (split + "-repeat"))
            if reference != repeated:
                raise RuntimeError("Unstable Java oracle; evaluation suite not frozen")
            payload["tasks"][task][split] = {"cases": rows, "reference": reference}
    save_json(path, payload)
    return FrozenSuite(path)


class FrozenSuite:
    def __init__(self, path):
        self.path = Path(path)
        self.digest = sha256(self.path)
        self._read()

    def _read(self):
        if sha256(self.path) != self.digest:
            raise RuntimeError("Frozen evaluation suite changed")
        payload = json.loads(self.path.read_text())
        if payload["source"] != verify_vendor() or payload["comparator_sha256"] != sha256(ROOT / "migration_lab/evaluation.py"):
            raise RuntimeError("Source/comparator differs from frozen evaluation protocol")
        if payload.get("schema") not in (1, 2):
            raise ValueError("Unsupported suite schema")
        if payload["schema"] == 2 and payload["generator_sha256"] != sha256(Path(__file__)):
            raise RuntimeError("Suite generator differs from frozen protocol")
        selected = TASKS if payload["schema"] == 1 else tuple(payload["tasks"])
        if not selected or any(t not in ALL_TASKS for t in selected):
            raise ValueError("Invalid suite tasks")
        if "commons_cli" in selected:
            from .cli_task import identity, contract
            from .scenarios import validate_cases, validate_rows
            if payload.get("task_identities", {}).get("commons_cli") != identity():
                raise RuntimeError("Stateful task implementation differs from frozen protocol")
            entries = payload["tasks"]["commons_cli"]
            for entry in entries.values():
                validate_cases(entry["cases"], contract())
                validate_rows(entry["reference"], entry["cases"])
            visible = {json.dumps(c["operations"], sort_keys=True) for c in entries["visible"]["cases"]}
            if any(json.dumps(c["operations"], sort_keys=True) in visible for c in entries["holdout"]["cases"]):
                raise ValueError("Visible and holdout scenarios overlap")
        for task in selected:
            for split in ("visible", "holdout"):
                entry = payload["tasks"][task][split]
                rows = entry["cases"]
                if (not rows or len({r["id"] for r in rows}) != len(rows)
                        or [r["id"] for r in rows] != [r["id"] for r in entry["reference"]]):
                    raise ValueError("Malformed frozen evaluation set")
        return payload

    def identity(self):
        data = self._read()
        return {"sha256": self.digest, "schema": data["schema"], "policy": data["policy"],
                "counts": {task: {split: len(value["cases"]) for split, value in splits.items()}
                           for task, splits in data["tasks"].items()}}

    def cases(self, task, split="visible", seed=None):
        return self._read()["tasks"][task][split]["cases"]

    def reference(self, task, split):
        return self._read()["tasks"][task][split]["reference"]
