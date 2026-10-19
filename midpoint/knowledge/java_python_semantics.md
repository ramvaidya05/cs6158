# Pilot semantic notes v1

- Java String.length/charAt count UTF-16 code units. Python str indexes Unicode
  code points. Where the source uses charAt, use UTF-16 code units, including for
  lengths, matching, and edit operations. Do not normalize Unicode inputs.
  Source: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/String.html
- Preserve the actual order of null, equality, empty-string, and limit checks.
  In this Levenshtein source, empty-string results are returned before the limit
  check. A naive min(full_distance, limit) changes observable behavior.
- Java integer division truncates toward zero. In JaroWinkler.matches the
  transposition count is divided as an integer. Its prefix loop has no automatic
  four-character cap: follow this source rather than a memorized algorithm.
- The source JaroWinkler declares m as float. Its intermediate arithmetic can
  round to binary32 before conversion to double. Python float is binary64; use
  explicit binary32 rounding where necessary (standard-library struct).
  Source: https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html
- Standard-library names and semantics must be checked against the pinned
  runtime. This small static knowledge pack is not a vector RAG system.
