"""Hand-authored harness fixture, derived from the vendored MIT-licensed source."""


def units(s):
    raw = s.encode("utf-16-le", "surrogatepass")
    return [raw[i] + 256 * raw[i + 1] for i in range(0, len(raw), 2)]


def run(a, b, operation="distance", parameter=None):
    if a is None or b is None:
        raise ValueError("Strings must not be null")
    if a == b:
        return 0
    a, b = units(a), units(b)
    if not a:
        return len(b)
    if not b:
        return len(a)
    limit = 2147483647 if parameter is None else parameter
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a):
        current = [i + 1]
        for j, y in enumerate(b):
            current.append(min(current[j] + 1, previous[j + 1] + 1,
                               previous[j] + (x != y)))
        if min(current) >= limit:
            return limit
        previous = current
    return previous[-1]
