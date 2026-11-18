# Midpoint annotation follow-up — November 17, 2026

This note answers the annotations in the three-page midpoint progress report.
The report describes the October state. The experiment evidence and milestone
changes made afterward are in [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md).

## What the three components actually do

The Migration role is the only model-driven component. It assembles the pinned
Java source and approved semantic notes, requests a Python module, and can send
visible execution failures back for at most five repair rounds.

The Environment role is deterministic. It checks the trusted runners before
generation, executes candidates in disposable CPython and GraalPy containers,
records runtime status and resource failures, and may apply one allowlisted
GraalPy cache-path correction after a trusted permission failure.

The Testsuite role is also deterministic. It sends a case to the original Java
implementation through `java/src/main/java/lab/Harness.java`, then sends the
same input to the Python candidate through `migration_lab/worker.py` or
`containers/GuestHarness.java` plus `migration_lab/guest_driver.py`. It compares
typed values, exceptions, and—on Commons CLI—operation traces. The original
Java JUnit tests are a separate oracle/build regression; they are **not** run
directly on translated Python. The adapter code is authored and reviewed by the
project, not invented by the model during a trial.

## Cases, metrics, and guards

Each string task has **26 visible cases**: 20 reviewed common/edge pairs and six
task-specific parameter or similarity cases. This is a practical pilot coverage
choice, not a power calculation. The frozen evaluator adds 140/124/131 withheld
cases for Levenshtein/NormalizedLevenshtein/JaroWinkler, with explicit Unicode,
null, boundary, and numeric strata plus seeded random cases. The model receives
only visible failures during repair. A selected candidate is scored on withheld
cases after all selections freeze. The current suite is exposed in archived
evidence, so it should not be called a new blind benchmark.

The **3/3** live Levenshtein result counts complete task trials. **78/78 visible**
and **420/420 withheld** count case checks *per runtime*: 26 and 140 inputs,
respectively, repeated across three trials. CPython and GraalPy check the same
cases; they are not independent samples. No repair was triggered. Token counts
include model thinking output. Failed API calls with unknown usage retain a
conservative budget reservation; those amounts are not measured charges.

The Docker isolation tests are project-authored integration tests that actually
launch containers. The candidate has no network, no repository or credential
mount, a read-only root/source, one CPU, 128 processes, bounded memory and
scratch (CPython 256/64 MiB; GraalPy 1536/512 MiB), and per-execution time and
output limits. Containers mitigate generated-code risk; they do not prove
security against container-runtime vulnerabilities.

The controller hashes protected source, tests, and context, runs a trusted
preflight, refuses live code in local subprocess mode, reruns all visible cases
after each repair, rejects a checkpoint that loses previously passing cases,
and never feeds withheld failures to the model. One historical run was
invalidated after a protected test changed mid-run; it remains archived.

## Why environment repair is a separate experiment

Under normal conditions, we fix the environment first and score translation
correctness in that healthy setting. A separate, controlled fault asks whether
the Environment role adds operational value beyond fixed-environment code
repair. In the GraalPy cache experiment, the fixed environment cannot execute;
the bounded cache correction restores execution. That result is not a higher
semantic translation score. The reported policy handles this one fault and is
not a general environment-planning agent. The new failure-routing study checks
whether candidate errors and setup errors are separated in both runtimes.

## What has changed since the midpoint report

Commons CLI 1.9.0 now has a four-class, stateful slice and an explicit object
adapter. Its hand-written fixture/repair qualification passes in both rebuilt
containers. No live Commons CLI translation was scored: the generation request
returned HTTP 503. The live NormalizedLevenshtein and JaroWinkler requests have
also failed before producing candidates. Those are provider failures, not
observed incorrect translations. The seven-fault synthetic sensitivity study
detected all seven faults in both runtimes, but fractional JaroWinkler
transpositions escaped every visible case and failed withheld cases.

## Next experiments in priority order

1. With a securely configured key, validate one tiny generation call and record
   access/model/latency. Choose an available model and freeze its configuration.
   Run fixed three-trial batches for the two remaining string tasks and Commons
   CLI; keep every provider failure in the operational denominator.
2. On a fresh, independently frozen suite, compare one-shot, fixed-environment
   code repair, and environment-aware repair from identical initial translations.
   Report genuine visible-failure opportunities, final withheld results,
   regressions, attempts, token use, time, and unresolved runs. Keep controlled
   environment faults separate from natural translation accuracy.
3. Add independent Commons CLI semantic scenarios and source variants, rather
   than only renaming values in the same 20 templates. Bind the new protocol and
   Java oracle before seeing model scores. Evaluate actual methods exercised;
   do not call the four-class slice whole-repository validation.
4. Validate a larger error taxonomy with real recorded failures. Then compare
   raw visible failures against concise, evidence-linked reports on paired
   candidates. Pruned messages must retain the decisive Java/Python mismatch.
5. Generate `requirements.txt` only for a separately scoped task that permits
   external Python dependencies. The current string/CLI tasks require standard
   library code and prohibit model-driven package installation in the sandbox.
6. Attempt AlphaTrans on a matched Commons CLI source snapshot, subject scope,
   tests, runtime capability, model, and budget. The current 1.9.0 slice is not
   comparable to its published project-wide percentage.

This sequence addresses the reviewer's request for bigger benchmarks and more
evaluation while preserving the existing pilot evidence. A smaller or alternate
model can be a separate cohort; it must not be mixed into the Gemini 3.8 Flash
paired comparison.
