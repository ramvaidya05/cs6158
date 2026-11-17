import struct

def _to_utf16_code_units(s: str) -> list[int]:
    encoded = s.encode('utf-16-be', 'surrogatepass')
    return list(struct.unpack(f'>{len(encoded) // 2}H', encoded))

def _f32(val: float) -> float:
    return struct.unpack('>f', struct.pack('>f', float(val)))[0]

class JaroWinkler:
    DEFAULT_THRESHOLD = 0.7
    THREE = 3
    JW_COEF = 0.1

    def __init__(self, threshold: float = 0.7) -> None:
        self.threshold = float(threshold)

    def get_threshold(self) -> float:
        return self.threshold

    def similarity(self, s1: str | None, s2: str | None) -> float:
        if s1 is None:
            raise ValueError("s1 must not be null")
        if s2 is None:
            raise ValueError("s2 must not be null")
        if s1 == s2:
            return 1.0

        u1 = _to_utf16_code_units(s1)
        u2 = _to_utf16_code_units(s2)

        mtp = self._matches(u1, u2)
        m = _f32(mtp[0])
        if m == 0.0:
            return 0.0

        term1 = _f32(m / _f32(len(u1)))
        term2 = _f32(m / _f32(len(u2)))
        term3 = _f32(_f32(m - _f32(mtp[1])) / m)
        sum1 = _f32(term1 + term2)
        sum2 = _f32(sum1 + term3)
        j = float(_f32(sum2 / 3.0))
        jw = j

        if j > self.get_threshold():
            jw = j + min(self.JW_COEF, 1.0 / mtp[self.THREE]) * mtp[2] * (1.0 - j)
        return jw

    def distance(self, s1: str | None, s2: str | None) -> float:
        return 1.0 - self.similarity(s1, s2)

    def _matches(self, u1: list[int], u2: list[int]) -> list[int]:
        if len(u1) > len(u2):
            max_u = u1
            min_u = u2
        else:
            max_u = u2
            min_u = u1

        range_val = max(len(max_u) // 2 - 1, 0)
        match_indexes = [-1] * len(min_u)
        match_flags = [False] * len(max_u)
        matches = 0

        for mi in range(len(min_u)):
            c1 = min_u[mi]
            xi_start = max(mi - range_val, 0)
            xn = min(mi + range_val + 1, len(max_u))
            for xi in range(xi_start, xn):
                if not match_flags[xi] and c1 == max_u[xi]:
                    match_indexes[mi] = xi
                    match_flags[xi] = True
                    matches += 1
                    break

        ms1 = [min_u[i] for i in range(len(min_u)) if match_indexes[i] != -1]
        ms2 = [max_u[i] for i in range(len(max_u)) if match_flags[i]]

        transpositions = sum(1 for mi in range(len(ms1)) if ms1[mi] != ms2[mi])

        prefix = 0
        for mi in range(len(min_u)):
            if u1[mi] == u2[mi]:
                prefix += 1
            else:
                break

        return [matches, transpositions // 2, prefix, len(max_u)]

def run(a: str | None, b: str | None, operation: str = "distance", parameter: float | None = None) -> float:
    threshold = 0.7 if parameter is None else float(parameter)
    jw = JaroWinkler(threshold)
    if operation == "distance":
        return jw.distance(a, b)
    elif operation == "similarity":
        return jw.similarity(a, b)
    else:
        raise ValueError(f"Unknown operation: {operation}")
