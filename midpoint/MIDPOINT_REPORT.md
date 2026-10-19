# Midpoint report: Environment-in-the-Loop Java-to-Python Translation

Draft based on implementation and saved execution evidence, 19 October 2026.
Intended for approximately 2–3 pages after formatting; review team names and
course-specific formatting before submission.

## Progress toward the project objectives

Our project investigates whether execution feedback and environment-aware repair
can improve Java-to-Python translation. At midpoint, we have moved beyond paper
review and implemented a runnable prototype on a dependency-closed subset of
`java-string-similarity`: Levenshtein, NormalizedLevenshtein, and JaroWinkler. The
subset provides a tractable starting point for validating the evaluator before
expanding to larger libraries. We retained the original Java source, selected
upstream tests, license, and a fixed repository commit with file checksums.

The prototype separates the proposal's Migration, Environment, and Testsuite
responsibilities. The Migration component prepares source-grounded translation
requests and supports a configurable live-model adapter or recorded-response
replay. The Environment component prepares and checks execution paths, runs
programs with timeouts, and saves runtime evidence. The Testsuite component
compares observed behavior against Java. A controller coordinates these roles
and limits each task to one initial candidate and at most five repairs.
Environment and Testsuite are deterministic services at this stage; we have not
implemented a fully autonomous three-LLM-agent system.

The verification harness has three real execution paths. It runs the original
Java implementation as the reference, executes candidate Python under CPython,
and invokes candidate Python from Java through embedded GraalPy. This meets the
midpoint objective of establishing executable cross-language verification for
the selected primitive/string scope. It does not yet implement general Java
object conversion or state synchronization. The upstream JUnit tests validate
the Java reference; the Python candidates are checked using differential cases,
not a wholesale translation of those JUnit tests.

## Implemented experiments and concrete results

We created 26 visible cases and 20 withheld-from-prompt cases per task. Cases
exercise ordinary inputs, empty and equal strings, null handling, repeated
characters, Unicode, applicable parameter limits, and seeded generated inputs.
Expected outcomes come from execution of the original Java code, not from an
LLM. The visible reference is run twice to check repeatability. The comparator
has an explicit Java-null-exception mapping and fixed numeric tolerances; missing
results, nonfinite values, timeouts, and zero-test runs cannot count as success.

Our completed acceptance experiment is a clearly labeled synthetic replay. The
controller first receives a deliberately incorrect implementation that always
returns zero, then a hand-authored implementation preserving the upstream
behavior. This negative-control design verifies that the framework detects
incorrect behavior, supplies feedback, selects an improved candidate, and runs
the final checks. It is not a live-model accuracy experiment.

All three correct fixtures passed all 46 cases under both CPython and GraalPy:
138 task/case combinations and 276 successful runtime checks. The broken fixture
passed only 4 of 26 visible cases per task in each runtime, demonstrating that
the evaluator does reject incorrect behavior. Each replay completed after two
attempts. Separately, five selected upstream JUnit test methods and 33 Python
unit/component tests passed. The Python tests cover comparison rules, timeout
handling, malformed results, model-response parsing, replay restrictions,
regression rejection, stopping rules, and infrastructure failure handling.

We save prompts, candidate code, runtime output, failing cases, source hashes,
configuration, and baseline/final results. Candidate selection uses visible
results only. After selection freezes, both the original and selected candidate
are scored on the same withheld split; those outcomes are not fed back into
repair. The acceptance archive includes raw artifacts and checksums so another
developer can inspect and reproduce the results.

## Challenges and implementation lessons

Runtime setup was a concrete implementation challenge. Maven and GraalPy were
not initially available on PATH. We added project-local dependency setup rather
than requiring global installation. An initial GraalPy run then failed to import
its standard-library `json` module, although the resource dependency existed.
Configuring GraalVM's internal resource cache under a writable project-local
directory resolved the failure. The failed execution is retained as evidence.
The controller now performs a trusted runtime preflight before requesting a
translation, preventing that setup failure from being misreported as model
translation failure.

The source inspection and fixture implementation also exposed semantic hazards.
Java string indexing operates on UTF-16 code units, whereas Python normally
indexes Unicode code points. A translation can therefore pass ASCII examples
and still change supplementary-character behavior. The pinned JaroWinkler
implementation uses binary32 intermediate arithmetic, integer transposition
division, and a source-specific prefix rule. We encoded these verified facts in
a compact knowledge pack and implemented compatible fixtures. These are concrete
implementation lessons, not evidence that a live model made those mistakes.

Another challenge is distinguishing infrastructure progress from research
results. Astra assisted with prototype construction in the IDE; it was not
selected as an API translation model. We have implemented and mock-tested a live
Responses API adapter, but no live-model experiment has run. Consequently, we
cannot claim an increase in model translation accuracy. The public deterministic
withheld split also tests feedback separation, not confidential evaluation or
absence of training contamination.

## Remaining deliverables and completion outlook

We have completed the midpoint's core infrastructure: source reference,
dual-runtime verification, translation interface, bounded repair controller,
evidence recording, automated acceptance tests, and developer documentation.
The key outstanding empirical deliverable is a repeated live-model comparison
between one-shot translation and repair. The framework is ready to support that
work once an experimental model is configured and execution isolation is added.

Our next implementation priority is containerized execution. Current subprocess
timeouts and restricted environment variables are useful operational controls,
but local CPython execution is not an OS sandbox for untrusted code. Following
that, we will freeze an evaluation protocol, run independent model trials, and
report functional results alongside repair counts, tokens, latency, and failures.
We will then add bounded environment-remediation behavior and compare it with
ordinary fixed-environment test-feedback repair. That control is essential to
identify the specific contribution of environment-in-the-loop operation.

After the pilot, we plan a coherent Commons CLI slice with the necessary object
and state adapters. A matched AlphaTrans comparison, structured diagnostic
reports, and provenance-linked retrieval follow as time permits. Broader library
coverage and additional language pairs remain stretch goals. The current small
pilot cannot be compared directly against AlphaTrans's published validated-method
percentage, and it does not establish generalization.

The implemented foundation supports a feasible path to the narrowed semester
deliverable: a reproducible prototype and an honest pilot evaluation. Completion
of the broader proposal remains conditional on model access, isolation work,
and the complexity of the next library slice. Our priority is a defensible,
measured result rather than claiming all proposed extensions are already on track.

Evidence: `evidence/20261019T214029Z-verification-1aee5b7b/`; reproduction and
limitations: `README.md`; implementation ownership and next steps:
`DEVELOPER_HANDOFF.md`.
