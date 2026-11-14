"""Typed operation-sequence protocol shared by trusted candidate runners.

This module provides a narrow dispatch interface, not an OS security sandbox.
Expected observations are computed separately by the Java reference.
"""
import inspect
import re


def validate_cases(cases, contract):
    if not isinstance(cases, list) or not cases:
        raise ValueError("Nonempty scenario list required")
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "task", "operations"} or case["task"] != contract["task"]:
            raise ValueError("Invalid scenario envelope")
        if not isinstance(case["id"], str) or case["id"] in ids:
            raise ValueError("Unique string case IDs required")
        ids.add(case["id"])
        operations = case["operations"]
        if not isinstance(operations, list) or not 1 <= len(operations) <= contract["max_operations"]:
            raise ValueError("Invalid operation count")
        handles = {}
        for operation in operations:
            if not isinstance(operation, dict):
                raise ValueError("Operation must be an object")
            kind = operation.get("op")
            if kind == "new":
                if set(operation) != {"op", "class", "args", "save"}:
                    raise ValueError("Invalid constructor fields")
                cls = operation["class"]
                if not isinstance(cls, str) or cls not in contract["classes"] or "constructor" not in contract["classes"][cls]:
                    raise ValueError("Constructor not permitted")
                signature = contract["classes"][cls]["constructor"]
                returns = cls
            elif kind == "call":
                if set(operation) not in ({"op", "on", "method", "args"}, {"op", "on", "method", "args", "save"}):
                    raise ValueError("Invalid call fields")
                if not isinstance(operation["on"], str) or not isinstance(operation["method"], str):
                    raise ValueError("Receiver and method must be strings")
                cls = handles.get(operation["on"])
                signature = contract["classes"].get(cls, {}).get("methods", {}).get(operation["method"])
                if signature is None:
                    raise ValueError("Unknown receiver or method not permitted")
                returns = signature["returns"]
            else:
                raise ValueError("Operation not permitted")
            if returns == "CommandLine" and "save" not in operation:
                raise ValueError("CommandLine results require a handle")
            args = operation["args"]
            if not isinstance(args, list) or len(args) != len(signature["args"]):
                raise ValueError("Wrong argument count")
            for value, expected in zip(args, signature["args"], strict=True):
                check_argument(value, expected, handles)
            if "save" in operation:
                name = operation["save"]
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", name):
                    raise ValueError("Invalid handle")
                if name in handles or returns not in contract["classes"]:
                    raise ValueError("Handles must be fresh and object-valued")
                handles[name] = returns


def check_argument(value, expected, handles):
    if expected == "string":
        valid = isinstance(value, str) and len(value) <= 4096
    elif expected == "bool":
        valid = type(value) is bool
    elif expected == "strings":
        valid = isinstance(value, list) and len(value) <= 128 and all(isinstance(v, str) and len(v) <= 4096 for v in value)
    else:
        valid = isinstance(value, dict) and set(value) == {"ref"} and isinstance(value["ref"], str) and handles.get(value["ref"]) == expected
    if not valid:
        raise ValueError("Argument violates type contract: " + expected)


def validate_implementation(scope, contract):
    """Check the public callable surface before executing scenarios."""
    for name, spec in contract["classes"].items():
        cls = scope.get(name)
        if not isinstance(cls, type):
            raise TypeError("Candidate must define class " + name)
        if "constructor" in spec:
            inspect.signature(cls).bind(*([None] * len(spec["constructor"]["args"])))
        for method, sig in spec["methods"].items():
            fn = getattr(cls, method, None)
            if not callable(fn):
                raise TypeError("Missing callable " + name + "." + method)
            inspect.signature(fn).bind(*([None] * (1 + len(sig["args"]))))


def execute_scenario(scope, case, contract):
    objects, types, trace = {}, {}, []
    for index, operation in enumerate(case["operations"]):
        row = {"step": index}
        try:
            args = [objects[v["ref"]] if isinstance(v, dict) else v for v in operation["args"]]
            if operation["op"] == "new":
                cls = operation["class"]
                value = scope[cls](*args)
                returns = cls
            else:
                cls = types[operation["on"]]
                returns = contract["classes"][cls]["methods"][operation["method"]]["returns"]
                value = getattr(objects[operation["on"]], operation["method"])(*args)
            if returns in contract["classes"] and not isinstance(value, scope[returns]):
                raise TypeError("Object result violates contract")
            if "save" in operation:
                objects[operation["save"]], types[operation["save"]] = value, returns
            if returns in contract["classes"]:
                # Canonical first handle exposes alias preservation, not Python internals.
                value = {"ref": next(name for name, obj in objects.items() if obj is value)}
            elif returns == "void":
                if value is not None:
                    raise TypeError("Void operation returned a value")
            elif returns == "bool":
                if type(value) is not bool:
                    raise TypeError("Boolean result required")
            elif returns == "string?":
                if value is not None and not isinstance(value, str):
                    raise TypeError("String or null result required")
            elif returns in ("strings", "strings?"):
                if not (returns == "strings?" and value is None):
                    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                        raise TypeError("String list required")
                    value = list(value)  # Snapshot the observation before subsequent mutation.
            row.update(status="ok", value=value)
        except Exception as exc:
            row.update(status="exception", type=contract["exception_map"].get(type(exc).__name__, type(exc).__name__))
        trace.append(row)
        if row["status"] == "exception":
            # Stop at first exception: no later call can depend on an unbound result.
            break
    return {"id": case["id"], "status": "ok", "trace": trace}


def first_difference(expected, actual):
    """Return an observable mismatch, never a claim about a causal source line."""
    left, right = expected.get("trace", []), actual.get("trace", [])
    for index in range(max(len(left), len(right))):
        a = left[index] if index < len(left) else None
        b = right[index] if index < len(right) else None
        if not strict_equal(a, b):
            return {"step": index, "expected": a, "actual": b}
    return None


def strict_equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(strict_equal(v, b[k]) for k, v in a.items())
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def validate_rows(rows, cases):
    """Reject incomplete or malformed traces before semantic comparison."""
    for row, case in zip(rows, cases, strict=True):
        trace = row.get("trace")
        if row.get("status") != "ok" or not isinstance(trace, list) or not 1 <= len(trace) <= len(case["operations"]):
            raise ValueError("Invalid operation trace")
        for index, observation in enumerate(trace):
            if not isinstance(observation, dict) or type(observation.get("step")) is not int or observation["step"] != index:
                raise ValueError("Invalid trace step")
            if observation.get("status") == "exception":
                if set(observation) != {"step", "status", "type"} or not isinstance(observation["type"], str) or index != len(trace) - 1:
                    raise ValueError("Invalid terminal exception")
            elif observation.get("status") != "ok" or set(observation) != {"step", "status", "value"}:
                raise ValueError("Invalid observation")
        if trace[-1]["status"] != "exception" and len(trace) != len(case["operations"]):
            raise ValueError("Truncated operation trace")
