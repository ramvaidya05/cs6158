import struct

class Levenshtein:
    """
    The Levenshtein distance between two words is the minimum number of
    single-character edits (insertions, deletions or substitutions) required to
    change one string into the other.
    """

    def distance(self, s1: str, s2: str, limit: int = 2147483647) -> float:
        if s1 is None:
            raise ValueError("s1 must not be null")

        if s2 is None:
            raise ValueError("s2 must not be null")

        if s1 == s2:
            return 0.0

        b1 = s1.encode("utf-16-le", "surrogatepass")
        s1_units = struct.unpack(f"<{len(b1) // 2}H", b1)
        b2 = s2.encode("utf-16-le", "surrogatepass")
        s2_units = struct.unpack(f"<{len(b2) // 2}H", b2)

        if len(s1_units) == 0:
            return float(len(s2_units))

        if len(s2_units) == 0:
            return float(len(s1_units))

        v0 = list(range(len(s2_units) + 1))
        v1 = [0] * (len(s2_units) + 1)

        for i in range(len(s1_units)):
            v1[0] = i + 1
            minv1 = v1[0]
            c1 = s1_units[i]

            for j in range(len(s2_units)):
                cost = 0 if c1 == s2_units[j] else 1
                val = min(
                    v1[j] + 1,
                    v0[j + 1] + 1,
                    v0[j] + cost
                )
                v1[j + 1] = val
                if val < minv1:
                    minv1 = val

            if minv1 >= limit:
                return float(limit)

            v0, v1 = v1, v0

        return float(v0[len(s2_units)])


def run(a, b, operation="distance", parameter=None) -> float:
    lev = Levenshtein()
    if operation == "distance":
        if parameter is None:
            return lev.distance(a, b)
        return lev.distance(a, b, int(parameter))
    raise ValueError(f"Unsupported operation: {operation}")
