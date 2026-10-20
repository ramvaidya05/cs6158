def _to_utf16_code_units(s: str):
    raw = s.encode('utf-16-le', 'surrogatepass')
    return [raw[i:i + 2] for i in range(0, len(raw), 2)]


class Levenshtein:
    @staticmethod
    def distance(s1, s2, limit=2147483647):
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
                v1[j + 1] = min(
                    v1[j] + 1,
                    v0[j + 1] + 1,
                    v0[j] + cost
                )
                if v1[j + 1] < minv1:
                    minv1 = v1[j + 1]

            if minv1 >= limit:
                return float(limit)

            v0, v1 = v1, v0

        return float(v0[len2])


def run(a, b, operation="distance", parameter=None):
    limit = 2147483647 if parameter is None else int(parameter)
    return Levenshtein.distance(a, b, limit)
