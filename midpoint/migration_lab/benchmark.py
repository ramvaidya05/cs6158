"""Pinned pilot scope and deterministic case generation; expected values come from Java."""
import json
import random
from .storage import ROOT, sha256

TASKS = ("levenshtein", "normalized", "jaro_winkler")
SOURCE_DIR = ROOT / "vendor/java-string-similarity/src/main/java/info/debatty/java/stringsimilarity"
SOURCES = {"levenshtein": ["Levenshtein.java"],
           "normalized": ["Levenshtein.java", "NormalizedLevenshtein.java"],
           "jaro_winkler": ["JaroWinkler.java"]}


def verify_vendor():
    manifest = json.loads((ROOT / "vendor/java-string-similarity/SOURCE.json").read_text())
    base = ROOT / "vendor/java-string-similarity"
    for name, digest in manifest["files"].items():
        if sha256(base / name) != digest:
            raise RuntimeError(f"Vendored source changed: {name}")
    return manifest


def cases(task, split="visible", seed=6158):
    if task not in TASKS or split not in ("visible", "holdout"):
        raise ValueError("Unknown task or split")
    rows = []

    def add(a, b, operation="distance", parameter=None):
        rows.append({"id": f"{task}-{split}-{len(rows):03}", "task": task,
                     "a": a, "b": b, "operation": operation, "parameter": parameter})

    if split == "visible":
        pairs = [("", ""), ("", "abc"), ("abc", ""), ("abc", "abc"),
                 ("kitten", "sitting"), ("My string", "My tsring"), ("aaaa", "aa"),
                 ("ab", "ba"), ("ABC", "abc"), ("hello world", "hello  world"),
                 ("\u00e9", "e\u0301"), ("\U0001f600", ""), ("a\U0001f600b", "ab"),
                 ("\U0001f600", "\U0001f603"), ("\x00a", "a"), ("\n", "\r\n"),
                 (None, "abc"), ("abc", None), (None, None), ("MARTHA", "MARHTA")]
        for a, b in pairs:
            add(a, b)
        if task == "levenshtein":
            for a, b, limit in [("abc", "xyz", 1), ("abc", "xyz", 2), ("", "abcdef", 2),
                                ("abc", "abc", 0), ("abc", "xyz", 0), ("abc", "xyz", -1)]:
                add(a, b, parameter=limit)
        else:
            for a, b in pairs[:5] + [(None, "")]:
                add(a, b, operation="similarity")
    else:
        rng = random.Random(seed)
        alphabet = "abCD \u00e9\u0301\U0001f680\U0001f600"
        for n in range(16):
            a = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
            b = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
            operation = "distance" if task == "levenshtein" or n % 2 == 0 else "similarity"
            parameter = None
            if task == "levenshtein" and n % 4 == 0:
                parameter = rng.choice([-1, 0, 1, 2, 5])
            if task == "jaro_winkler" and n % 4 == 0:
                parameter = rng.choice([-1.0, 0.0, 0.7, 0.9])
            add(a, b, operation, parameter)
        add(None, "withheld")
        add("withheld", None)
        add("longcommonprefixA", "longcommonprefixB", "similarity" if task != "levenshtein" else "distance")
        add("\U0001f680\U0001f600", "\U0001f600\U0001f680")
    return rows
