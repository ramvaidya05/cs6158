import struct

INTEGER_MAX_VALUE = 2147483647


def _to_utf16_code_units(s: str) -> tuple:
    encoded = s.encode("utf-16-le", "surrogatepass")
    return struct.unpack(f"<{len(encoded) // 2}H", encoded)


class Levenshtein:
    def distance(self, s1: str, s2: str, limit: int = INTEGER_MAX_VALUE) -> float:
        if s1 is None:
            raise ValueError("s1 must not be null")
        if s2 is None:
            raise ValueError("s2 must not be null")

        if s1 == s2:
            return 0.0

        u1 = _to_utf16_code_units(s1)
        u2 = _to_utf16_code_units(s2)

        n1 = len(u1)
        n2 = len(u2)

        if n1 == 0:
            return float(n2)
        if n2 == 0:
            return float(n1)

        v0 = list(range(n2 + 1))
        v1 = [0] * (n2 + 1)

        for i in range(n1):
            v1[0] = i + 1
            minv1 = v1[0]

            for j in range(n2):
                cost = 0 if u1[i] == u2[j] else 1
                v1[j + 1] = min(
                    v1[j] + 1,
                    v0[j + 1] + 1,
                    v0[j] + cost,
                )
                if v1[j + 1] < minv1:
                    minv1 = v1[j + 1]

            if minv1 >= limit:
                return float(limit)

            v0, v1 = v1, v0

        return float(v0[n2])


def run(a, b, operation="distance", parameter=None) -> float:
    if operation != "distance":
        raise ValueError(f"Unsupported operation: {operation}")

    limit = INTEGER_MAX_VALUE if parameter is None else int(parameter)
    lev = Levenshtein()
    return lev.distance(a, b, limit)
