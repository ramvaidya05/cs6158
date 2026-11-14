"""Hand-authored harness fixture, derived from the vendored MIT-licensed source."""
import struct


def f32(x):
    return struct.unpack("!f", struct.pack("!f", x))[0]


def units(s):
    raw = s.encode("utf-16-le", "surrogatepass")
    return [raw[i] + 256 * raw[i + 1] for i in range(0, len(raw), 2)]


def run(a, b, operation="distance", parameter=None):
    if a is None or b is None:
        raise ValueError("Strings must not be null")
    if a == b:
        similarity = 1.0
    else:
        a, b = units(a), units(b)
        large, small = (a, b) if len(a) > len(b) else (b, a)
        window = max(len(large) // 2 - 1, 0)
        indexes = [-1] * len(small)
        flags = [False] * len(large)
        for i, char in enumerate(small):
            for j in range(max(i - window, 0), min(i + window + 1, len(large))):
                if not flags[j] and char == large[j]:
                    indexes[i], flags[j] = j, True
                    break
        first = [small[i] for i, j in enumerate(indexes) if j != -1]
        second = [large[j] for j, flag in enumerate(flags) if flag]
        if not first:
            similarity = 0.0
        else:
            transpositions = sum(x != y for x, y in zip(first, second)) / 2
            prefix = 0
            for x, y in zip(small, large):
                if x != y:
                    break
                prefix += 1
            m = f32(len(first))
            jaro = f32(f32(f32(m / len(a)) + f32(m / len(b))) +
                       f32(f32(m - transpositions) / m))
            similarity = f32(jaro / 3)
            threshold = 0.7 if parameter is None else parameter
            if similarity > threshold:
                similarity += min(0.1, 1.0 / len(large)) * prefix * (1.0 - similarity)
    return 1.0 - similarity if operation == "distance" else similarity
