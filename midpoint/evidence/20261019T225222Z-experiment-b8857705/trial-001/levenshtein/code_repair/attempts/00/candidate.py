import struct

def _to_utf16_code_units(s: str):
    encoded = s.encode('utf-16-le', 'surrogatepass')
    return struct.unpack(f"<{len(encoded) // 2}H", encoded)

class Levenshtein:
    def distance(self, s1, s2, limit=2147483647):
        if s1 is None:
            raise ValueError("s1 must not be null")
        if s2 is None:
            raise ValueError("s2 must not be null")

        if s1 == s2:
            return 0.0

        u1 = _to_utf16_code_units(s1)
        u2 = _to_utf16_code_units(s2)

        if len(u1) == 0:
            return float(len(u2))

        if len(u2) == 0:
            return float(len(u1))

        lim = 2147483647 if limit is None else int(limit)

        v0 = list(range(len(u2) + 1))
        v1 = [0] * (len(u2) + 1)

        for i in range(len(u1)):
            v1[0] = i + 1
            minv1 = v1[0]

            for j in range(len(u2)):
                cost = 0 if u1[i] == u2[j] else 1
                v1[j + 1] = min(
                    v1[j] + 1,
                    v0[j + 1] + 1,
                    v0[j] + cost
                )
                minv1 = min(minv1, v1[j + 1])

            if minv1 >= lim:
                return float(lim)

            v0, v1 = v1, v0

        return float(v0[len(u2)])

def run(a, b, operation="distance", parameter=None):
    if operation != "distance":
        raise ValueError(f"Unsupported operation: {operation}")
    lev = Levenshtein()
    if parameter is None:
        return lev.distance(a, b)
    return lev.distance(a, b, parameter)
