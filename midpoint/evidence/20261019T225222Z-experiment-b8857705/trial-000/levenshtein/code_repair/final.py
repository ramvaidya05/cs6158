import math


def _to_utf16_code_units(s: str):
    return memoryview(s.encode("utf-16-le", "surrogatepass")).cast("H")


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

        u1 = _to_utf16_code_units(s1)
        u2 = _to_utf16_code_units(s2)
        len1 = len(u1)
        len2 = len(u2)

        if len1 == 0:
            return float(len2)
        if len2 == 0:
            return float(len1)

        v0 = list(range(len2 + 1))
        v1 = [0] * (len2 + 1)

        for i in range(len1):
            v1[0] = i + 1
            minv1 = v1[0]
            c1 = u1[i]

            for j in range(len2):
                cost = 0 if c1 == u2[j] else 1
                val = v1[j] + 1
                v_rem = v0[j + 1] + 1
                v_sub = v0[j] + cost
                if v_rem < val:
                    val = v_rem
                if v_sub < val:
                    val = v_sub
                v1[j + 1] = val
                if val < minv1:
                    minv1 = val

            if minv1 >= limit:
                return float(limit)

            v0, v1 = v1, v0

        return float(v0[len2])


def run(a, b, operation="distance", parameter=None) -> float:
    limit = 2147483647 if parameter is None else int(parameter)
    return Levenshtein().distance(a, b, limit)
