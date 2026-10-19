# Frozen pilot translation contract v1

Return a complete standalone Python module defining:
`run(a, b, operation="distance", parameter=None)`.

Implement the supplied Java task, including its dependency closure. Inputs are
strings or None. Output is a finite number. Map Java NullPointerException to
Python ValueError; do not silently accept null. Exception messages are recorded
but not scored. Preserve source behavior even where a different algorithm seems
more idiomatic. Only Python standard-library imports are allowed. Do not call
Java, subprocesses, network services, or files. No test changes or hardcoded
answers. No fallback to the original Java implementation.

For Levenshtein, operation is distance and parameter is its optional int limit.
For NormalizedLevenshtein, operation is distance or similarity; parameter is None.
For JaroWinkler, operation is distance or similarity and parameter is the optional
constructor threshold. Invalid operation names are outside this pilot's domain.

All runtimes use the same frozen floating-point comparator: abs_tol=rel_tol=1e-9.
This is test-supported numeric parity, not a proof of full language equivalence.
