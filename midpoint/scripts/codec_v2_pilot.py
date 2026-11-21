"""Prospective Codec-only v2 pilot; never pool with the historical v1 scores.

The protocol adds visible Unicode strata after v1 exposed coverage gaps.
Fresh held-out values are frozen by the Java oracle before generation.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import codec_hex_pilot as pilot

original_cases = pilot.cases
original_prompt = pilot.prompt


def cases():
    visible = original_cases()["visible"]
    for value in ("Ｆ１", "٢a", "𝟑b", "²a", "g1"):
        visible.append({"id": f"codec-v2-visible-{len(visible)}", "task": pilot.TASK,
                        "operation": "decode", "data": value, "lower": True})
    rng = random.Random(20261121)
    held = []
    def add(operation, data, lower=True):
        held.append({"id": f"codec-v2-holdout-{len(held)}", "task": pilot.TASK,
                     "operation": operation, "data": data, "lower": lower})
    for n in range(50):
        data = [rng.randrange(256) for _ in range(rng.randrange(1, 40))]
        add("encode", data, n % 2 == 0)
        add("decode", bytes(data).hex().upper() if n % 2 else bytes(data).hex())
    for value in ("Ｃ９", "９ｅ", "٤B", "६c", "𝟖e", "⁴f", "Ⅳa", "b\x00", "ab7", "a\n"):
        add("decode", value)
    return {"visible": visible, "holdout": held}


def prompt(previous=None, failures=None):
    return original_prompt(previous, failures) + (
        "\nTARGET RUNTIME CONTRACT: execute in CPython 3.12 and GraalPy 25.0.0. "
        "The pinned GraalPy runtime lacks unicodedata.digit. Preserve Java char[] "
        "UTF-16 code-unit behavior. Source Character.digit accepts decimal digits "
        "and ASCII/fullwidth hexadecimal letters, not arbitrary numeric symbols. "
        "Use portable standard-library operations; do not install packages.")


if __name__ == "__main__":
    pilot.MODEL = "gemini-3.5-flash"
    pilot.MAX_OUTPUT = 4096
    pilot.MAX_TOTAL_TOKEN_RESERVATION = 40000
    pilot.MAX_SPEND_USD = 0.15
    pilot.cases = cases
    pilot.prompt = prompt
    # Rates are explicit experiment accounting assumptions, not invoice claims.
    budget_type = pilot.SpendBudget
    pilot.SpendBudget = lambda limit, _input, _output, path: budget_type(limit, 1.50, 9.00, path)
    raise SystemExit(pilot.main())
