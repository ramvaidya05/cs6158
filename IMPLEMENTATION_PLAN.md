# Environment-in-the-Loop Java-to-Python Translation: Research and Implementation Plan

Prepared 19 October 2026. Updated after midpoint implementation: the runnable prototype is in [midpoint/](./midpoint/README.md). Three-task synthetic replay acceptance passes in CPython and Java-embedded GraalPy. This demonstrates infrastructure, not live-model translation performance; see the checkpoint below for the first live result. See the [developer handoff](./midpoint/DEVELOPER_HANDOFF.md) and [midpoint report draft](./midpoint/MIDPOINT_REPORT.md) for the current implementation and evidence.

The [one-day midpoint plan](./MIDPOINT_TODAY_PLAN.md) records the original scope. The longer milestones below remain a research roadmap, not a statement that every described component is implemented; their original schedule does not apply to today's midpoint target.

Current implementation checkpoint: [experiments and results](midpoint/EXPERIMENT_RESULTS.md).
Live Gemini experiments now cover Levenshtein and a four-class Commons CLI slice.
The stronger CLI profile contains 36 visible and 20 separately authored holdout
scenarios, detects eight injected faults in both runtimes, and supports paired
basic-versus-operation-feedback studies. Five fresh trials yielded one fully
observed case where operation feedback repaired a failure that basic feedback did
not; another comparison was budget-limited. See the results for exact denominators
and limitations. Multi-module translation and cross-trial lesson reuse are still
future work, not delivered features.

Latest engineering checkpoint: [retry memory and CLI v3 observations](midpoint/RETRY_MEMORY_OBSERVATIONS.md). The evaluator now supports 32 methods across five CLI classes, with 44 visible and 28 holdout scenarios. Arm-local retry memory, pruned diagnostics, and standard-library-only requirements generation are implemented. These changes are locally qualified; the live results above still refer to the earlier four-class protocol. Cross-trial reuse, arbitrary package installation, multi-module translation, and the matched AlphaTrans comparison remain outstanding.

Latest live-study checkpoint: [CLI v3 observations](midpoint/CLI_V3_LIVE_OBSERVATIONS.md). The scoped 32-method main study and separate memory ablation have now run with fresh Gemini responses (three trials each). Main arms all passed 3/3 without repairs; in the separate memory cohort both repair arms improved full-task success from 1/3 to 3/3 with identical one-retry recoveries. Memory superiority is not established. A semantic holdout gap was identified and is recorded for a future suite version; existing scores were not revised. Matched AlphaTrans evaluation and repository-scale work remain outstanding.

## 1. Recommended research direction

Build a small, reproducible Java-to-Python translation system that combines dependency-aware translation, executable Java reference behavior, GraalPy validation, and bounded repair of both target code and its environment. Start by validating the evaluator, then add translation, then repair, and finally investigate diagnostic reports and broader generalization.

The research question is: **Under a fixed evaluation protocol and measured resource budget, does environment-aware execution and repair improve observed behavioral parity over one-shot translation and ordinary test-feedback repair?** A separate comparison asks how it performs against AlphaTrans on matched subjects.

The contribution should be an implemented, evaluated adaptation of the Environment-in-the-Loop architecture, with trustworthy measurements of translation and environment failures. Test feedback, GraalVM, RAG, and agent roles are not individually new contributions. Higher performance remains a hypothesis until experiments are run.

## 2. What the supplied documents establish

### AlphaTrans [P1]

AlphaTrans is already an iterative, execution-guided Java-to-Python system. It transforms language-specific constructs, extracts dependency information, builds a Python skeleton, translates fragments in reverse call order, retrieves type documentation, and validates with GraalVM and translated tests. Sections 5–6 explain these mechanisms. Its GraalVM bridge includes object conversion, state synchronization, alias preservation, and exception propagation; this is substantially more than invoking Python from Java.

Its main experiment uses ten projects and 4,654 application method fragments. The published figures distinguish several different measurements:

- 96.40% syntactic correctness across all 17,874 fragments, including fields and tests.
- 25.14% of application method fragments functionally validated relative to available tests; 27.03% runtime-validated.
- 43.43% of application method fragments not exercised by source tests.
- 15.84% of application method fragments encountering limitations of the GraalVM validation approach.
- 24.50% Graal success over all application method fragments, or 43.30% over source-test-covered methods.
- 27.95% functional validation when substituting GPT-4o in the model ablation.

These are reported in the abstract, Table 2 and sections 7.2.2/7.6.2. Thus the slides' approximate 26% should not be described as universal translation accuracy or as evidence that 74% of code is incorrect. Uncovered and unsupported methods are unvalidated. Nor should an improvement over this aggregate on a smaller selected library be called an improvement over AlphaTrans. For example, Table 2 reports **70.70% Graal success for Commons CLI**, much higher than the aggregate; its translated-test pass rate is a separate metric, 10.08%.

Section 7.3 identifies API mismatches, language behavior differences, and dependency-related failure propagation. Section 7.5 shows that test coverage affects how much can be validated. Subject preparation also removed unsupported third-party dependencies and involved manual type-map refinement. Those transformations and manual inputs must be accounted for in a reproduction.

One useful caution: the illustrative null-concatenation repair in section 7.3.2, PDF page 15, uses `str(None)`. That avoids a Python type error but produces `"None"`, whereas Java string conversion of null produces `"null"` [W5]. As printed, the example does not establish exact output parity. Treat paper examples as evidence to investigate, not automatically correct entries in a retrieval database.

### Environment-in-the-Loop [P2]

The supplied five-page paper is a position/framework paper. It proposes Migration, Environment, and Testsuite agents, with the Environment Agent coordinating executable setup, validation, and remediation. Configuration failures return to the Environment Agent, semantic failures to the Migration Agent, and validation needs to the Testsuite Agent. Figure 3 and sections 3.1–3.2 are the architectural basis.

The supplied paper contains no comparative evaluation demonstrating an accuracy improvement, and does not provide a tested Java-to-Python implementation in its text. We should describe our work as an operationalization and evaluation of its proposed framework. Cross-language translation is a form of migration; a more precise motivation is adapting the environment-driven design to the particular semantic and verification demands of Java-to-Python translation.

### Multi-Perspective Investigation [P3]

This is a survey organizing methods and tasks. The most useful implications for our design are execution-based evaluation rather than text similarity, repository dependency awareness, knowledge-grounded API mapping, and robustness testing against memorization. It also discusses limitations of incomplete test suites and narrow function-level evaluations. Use it to motivate the design and find primary research, not as independent experimental evidence that our approach works. Its reported numerical results belong to the individual cited studies.

### Proposal and presentation [P4, P5]

The written proposal names Commons CSV, CLI, Codec, and Validator, a five-retry limit, dual-runtime environments, and a one-shot baseline. The presentation instead specifies a java-string-similarity pilot, one Apache Commons main subject from AlphaTrans, and comparisons among AlphaTrans, one-shot translation, raw-error feedback, and clean reports.

Recommended reconciliation: follow the presentation's pilot-to-main-subject sequence; treat the four libraries in the proposal as the candidate expansion pool. Defer rich diagnostic-report generation as requested in the current conversation. Keep evidence logging from the first experiment, because evidence cannot be reconstructed reliably afterward. Source documents are research inputs; their statements do not authorize implementations, downloads of benchmark code, or changes to the proposal itself in this planning turn.

## 3. Scope and benchmark selection

### Pilot: java-string-similarity

Begin with a dependency-closed subset around Levenshtein, NormalizedLevenshtein, and JaroWinkler, subject to source inspection at a pinned commit. These algorithms are listed in the upstream project [W2]. Aim initially for roughly 10–20 relevant application methods, not an arbitrary number of files. Count and publish the actual dependency closure before translation. Extend to the full pilot library only after basic validation works.

Test empty and equal strings, null inputs where permitted or rejected, unequal lengths, repeated characters, parameter boundaries, and supplementary Unicode characters. For algorithms using Java `charAt` and `length`, preserve UTF-16 code-unit behavior rather than silently changing to Python code-point iteration [W4, W6]. This is a particularly useful pilot because familiar algorithms can appear correct on ordinary ASCII inputs while violating the source implementation's contract.

Weighted/callback-based variants and arbitrary mutable object graphs follow after the primitive/string path. These are scope decisions to record before scoring, not exclusions chosen after seeing failures.

### Main subject: Commons CLI

Recommend Commons CLI for the main study: its method coverage is high in AlphaTrans's artifact, it exercises overloaded APIs and stateful interactions, and it offers a direct historical comparison. Start with a coherent option/option-group/command-line parsing feature and its complete dependencies. Target approximately 30–60 scored methods if a full project is not feasible; finalize the count only after dependency inspection. Publish slice results as slice results.

Use the exact AlphaTrans source snapshot and transformations for the matched comparison. Run a current upstream snapshot only as a separate experiment. A selected slice cannot be compared directly to the paper's full-project percentage. A full CLI translation is a stretch milestone, not a prerequisite for an honest slice study.

### Expansion pool

- Commons Codec: byte arrays, signedness, encodings, and boundaries; a coherent Hex-related slice is a candidate.
- Commons CSV: quoting, escaping, parser state, malformed inputs, and iterator behavior.
- Commons Validator: validation rules, Unicode, and numeric/string edge cases.

Choose additional subjects using predeclared criteria: reproducible source build, meaningful assertion coverage, manageable dependency closure, and semantic diversity. Keep a selection/exclusion ledger. If we stay with a pilot and one main library, describe the result as a case study, not broad generalization across Java programs.

## 4. Verification harness: implement this first

The harness is the independent machinery that prepares a task, executes code, compares observations, records outcomes, and enforces the experiment budget. An LLM must not decide whether its own output passes.

### A. Frozen source oracle

Pin source commit, selected APIs, dependencies, test IDs, build commands, encoding, locale, timezone, and input seeds. Build and run Java tests before admitting a task. Confirm reproducibility with repeated source runs. Keep the reference source and reference environment immutable throughout translation.

Describe each task with a manifest containing task ID, source hash, method signatures, dependency closure, permitted target dependencies, observable behavior, comparator rules, resource limits, and evaluation split. Bind oracle outputs to the source/environment/input hashes. An unstable Java oracle is a preparation failure, not a translation result.

### B. Three execution paths

1. **Java reference:** execute the original implementation with fixed test inputs and record outputs, exceptions, and relevant state transitions.
2. **Java-to-Python bridge:** embed GraalPy through the Java Polyglot API. Preserve Java-facing signatures using scoped, reviewed adapters; run eligible original Java tests against Python implementations. Maven/Gradle embedding is supported by the current GraalPy documentation [W3]. The bridge must be implemented explicitly.
3. **Standalone Python:** run the composed Python package under a pinned CPython version, using the same differential cases. Confirm that successful translations do not depend on calling back into the Java implementation.

Use a GraalPy/Python/JDK combination whose compatibility is demonstrated during the first milestone; do not assume the host's Python version matches GraalPy. Historical AlphaTrans reproduction should retain its own documented runtime configuration. Pin exact versions and image digests after the smoke test rather than filling the plan with untested version combinations.

### C. Isolation and integration are separate claims

For isolated method validation, AlphaTrans's approach replaces one Java method body with a polyglot call while other methods remain Java. If adopting this technique, reuse or adapt its bridge where practical rather than rebuilding general object isomorphism. Label these successes as isolated-method results.

For integrated validation, execute the complete selected Python dependency closure. The selected functionality must not fall back to Java. Report integration separately: individually passing methods do not prove that the composed Python module works.

For the first pilot, support strings, booleans, bounded integers, floating-point values, null, and a narrow set of arrays/containers. Expand to object handles, identity, aliasing, mutation synchronization, and callbacks only when the next benchmark requires them. Record unsupported types explicitly. Serializing an object graph into plain JSON is not sufficient to preserve aliasing or identity.

### D. Define behavioral equivalence before generating code

Compare values and their shapes/types where the API distinguishes them, relevant mutated arguments and object state, exception categories, and observable side effects. For stateful APIs, compare sequences of calls, not just a fresh object's first return value.

Use exact comparison for integers, bytes, strings, and contractually ordered sequences. Specify floating-point tolerances per API before seeing candidate output, including policies for NaN, infinities, and signed zero when relevant. Compare exception messages only when they are part of the source contract/test expectations. Normalize genuinely irrelevant runtime details, such as temporary directory prefixes, using frozen rules.

Do not sort all collections, coerce all values to strings, widen tolerances after failures, or mask integer overflow only in the comparator. Those actions can conceal semantic errors. Correct Java compatibility belongs in the translated implementation or explicitly shared compatibility helpers.

### E. Validate the validator

Before any LLM run, verify:

- A small, manually checked Python implementation agrees with Java through both GraalPy and CPython.
- Deliberate changes to a result, an exception, and a supported state mutation are detected.
- No-op or bypassed bridge dispatch is detected through instrumentation showing the Python target was executed.
- A bridge type-conversion problem is distinguishable from a Python semantic mismatch.
- Tests and comparator hashes remain unchanged, zero-tests-run is an error, and timeouts are recorded.

Manual reference fixtures are harness development assets, not benchmark solutions exposed to the translator. A harness defect discovered during evaluation invalidates affected runs; fix it and rerun all affected systems under the revised protocol.

## 5. Translation architecture and agent responsibilities

Use an explicit controller with recorded states: prepare, inspect, translate, build, test, classify, repair, regression-test, and finish. Store checkpoints and exact artifacts between states. A simple state machine is enough initially; a large agent framework is not required.

**Migration role (M):** receives a scoped Java fragment/class, dependency and signature information, verified context, and available feedback; proposes Python code or a patch. Preserve behavior first. Avoid unsolicited validation, exception swallowing, and API redesign. It may edit only the candidate Python implementation and declared target packaging files.

**Environment role (E):** prepares reproducible sandboxes, verifies installed dependencies and runtime constraints, executes controlled build/run commands, and handles permitted target-environment repairs. Keep the source oracle frozen. A missing import is not automatically a missing package: first check whether the referenced API exists and was permitted. Dependency changes must remain within the target contract and be logged.

**Testsuite role (T):** executes frozen visible tests, checks original Java behavior, produces observable comparisons and coverage, and guards against regressions. Initially it is deterministic. Later it can propose additional source-grounded development inputs, but it must never rewrite scored assertions to accommodate a candidate.

**Controller:** owns iteration budgets, patch authorization, checkpoint selection, artifact hashes, error routing, and final status. Separate infrastructure errors, bridge limitations, target syntax/import errors, semantic mismatches, and unknown failures. An ambiguous failure remains unknown until supported by evidence.

Start with one LLM-driven M role and deterministic E/T services. This is a staged implementation of the paper's responsibilities, not yet a faithful three-LLM-agent implementation. Add bounded E-agent planning and T-agent test generation only when useful and evaluate their cost and incremental value. Roles can share a model while keeping distinct permissions and histories.

### Translation granularity and dependency handling

Extract real symbols and signatures using an AST plus symbol resolution, or reuse AlphaTrans's analysis artifacts. Syntax-only parsing is insufficient for reliable overloaded dispatch and call resolution. For a small pilot, manually review the generated dependency manifest.

Maintain one authoritative source-to-target symbol map. Construct package/class skeletons before filling methods. Translate callees before callers; treat strongly connected components as groups with a fixed interface contract and integration checks. Include constructor behavior, class/instance state, imports, and already validated callee contracts in the context. If source transformations are needed, retain the original and rerun source tests on the transformed copy.

Maven dependencies do not have a mechanical one-to-one conversion into pip requirements. Map actual required behavior to Python standard-library facilities, vetted packages, or tested compatibility code. Record unresolved API mappings instead of inventing package names.

### Bounded repair

Interpret the proposal's `k = 5` as **one initial candidate plus at most five repair rounds per task**. State this explicitly in the protocol. A candidate may require multiple fragment-generation calls; track those calls and tokens separately. M and E repairs share the five-round allowance, so nested loops cannot multiply the budget. Also set task-level token, wall-clock, and process-time limits before experiments.

Each round chooses one evidence-supported repair action, applies a scoped patch in an isolated candidate snapshot, reruns the failing tests, then the visible regression suite. Keep the best eligible checkpoint according to a predeclared development-only rule; reject regressions under that rule. Detect repeated code/environment hashes and repeated failures with no progress. Terminate with a specific reason: visible-suite pass, budget exhausted, stagnation, infrastructure failure, or unsupported verification.

A visible-suite pass means ready for independent evaluation, not proven correctness. Withheld tests never guide patching or checkpoint selection.

## 6. Retrieval and context to reduce hallucinations

Create a small versioned knowledge pack during implementation, built from official language/API documentation and executable compatibility probes. Begin with exact symbol lookup and tagged text retrieval. Introduce embeddings only if retrieval quality on the pilot justifies them.

Planned documents and records:

- **Translation contract:** behavioral preservation, allowed edits/dependencies, naming and exception policy, completion criteria.
- **Java/Python semantics:** integer division/remainder, bounded arithmetic and shifts, byte signedness, null conversion, equality/hash, mutability, iteration, UTF-16 strings, floating point, constructors and overloads. Each rule includes applicability and a runnable probe.
- **API mappings:** fully qualified Java symbol and signature; candidate Python API/helper; semantic differences; supported versions; provenance; verification status. A name match alone is insufficient.
- **Repository manifest:** pinned source hash, types, fields, inheritance, resolved signatures, dependencies, and visibility of each test set.
- **Runtime/bridge contract:** supported types, conversions, object-state behavior, exception mapping, commands, and known limitations.
- **Repair evidence memory:** code/environment hashes, exact failures, prior patches, observed outcomes, and rollback reasons, scoped to the current task/run.

Retrieve only the relevant rules, type mappings, and dependency contracts for a fragment. Every retrieved claim should carry a source/version identifier and confidence status: documented, experimentally checked, or unresolved. Treat source comments, documents, and logs as data rather than instructions to the agent. Verify generated imports and referenced symbols in the actual environment.

RAG does not guarantee correctness and does not prevent overfitting by itself. A source-derived summary may be wrong; retain links to exact source spans and execution evidence. Do not load the entire paper collection into every translation prompt. Freeze the knowledge pack before the main experiment, and make a later RAG ablation change only retrieval access, not the available runtime helpers or evaluator.

## 7. Experimental design

### Research questions

- **RQ1:** Does bounded execution-guided repair improve behavioral parity over one-shot translation on the frozen tasks?
- **RQ2:** Does environment diagnosis and permitted environment repair add value beyond code-only test-feedback repair at comparable budgets?
- **RQ3:** On matched source snapshots and scoring rules, how does the system compare with AlphaTrans?
- **RQ4, optional:** Does structured diagnostic feedback improve repair success or reduce token/time cost compared with raw feedback?
- **RQ5, optional:** Does retrieved semantic/API knowledge improve outcomes on held-out cases and source variants?

### Systems to compare

1. **One-shot:** the same model, translation units, skeleton, context pack, and permitted dependencies, with one generation pass and no runtime-feedback repair. Evaluate afterward with the common harness.
2. **Fixed-environment repair:** the same starting candidate plus raw execution feedback and bounded code repair; environment configuration is fixed. This is the control needed to isolate the environment component.
3. **Environment-in-the-loop, raw:** the same starting candidate and budget, with evidence-based routing and permitted target-environment repairs. Raw logs follow a deterministic truncation policy; full logs are retained.
4. **AlphaTrans:** attempt a reproduction on the matched Apache subject. Separate its published configuration from a same-model/common-harness comparison. Record any adaptations as such.
5. **Environment-in-the-loop, structured, later:** identical to system 3 except feedback representation. Any report-generation model calls count toward the resource budget.

The first three are the minimum controlled comparison. The AlphaTrans attempt is part of the main-study plan, with a short feasibility gate. The structured arm is deferred in line with the user's current scope. If AlphaTrans cannot run within the allotted setup effort, document the cause and restrict the claim to the runnable baselines; archived numbers provide context, not a controlled win.

To claim improvement over AlphaTrans, use matching subject boundaries, tests, validation capabilities, model conditions, and measured budgets, or explicitly identify confounders. Its current artifact exposes prepared subjects and reproduction scripts [W1]. Do not expose its manually repaired Python outputs to our translator or retrieval index.

### Fairness and resource accounting

Use one fixed model snapshot/configuration across the controlled systems; log the provider/model ID, prompt version, decoding settings, available seed, input/output tokens, errors, and latency. No particular commercial model is required by this plan. Select one based on available access and budget before implementation runs.

Use three independent generation replicates as a practical initial target. Pair systems 1–3 by starting each replicate from the same initial translation. Low temperature is not a guarantee of determinism. If only one replicate is affordable, label results exploratory.

Give iterative arms equal token, time, and repair-round caps. One-shot inherently spends less; report performance against cost and call count rather than claiming that its comparison isolates feedback at equal compute. A repeated-sampling, no-feedback control is an optional additional way to test the value of feedback over extra generation effort.

Run natural translation tasks first. If studying environment repair separately, add a clearly labeled stress experiment with controlled, recoverable target-environment problems. Use the same perturbations across arms and forbid changing the Java reference contract. Do not mix deliberately introduced environment faults into the main translation-accuracy score. If the curated tasks all have healthy, simple environments, RQ2 may show little benefit; that is a valid finding.

### Split and contamination controls

Use the pilot for harness/prompt development. Freeze prompt templates, retrieval rules, comparator policy, and budgets before the main subject. Keep visible development tests separate from evaluator-only generated edge cases and randomized inputs. Generate expected outcomes by executing the pinned Java implementation, not by asking an LLM to invent answers. Audit that new cases exercise the intended API and are stable.

Existing public Java tests may appear in the model's training data; do not call them unseen. Withheld evaluation files and expected results must be outside agent-readable mounts. Do not feed final-evaluation failures into repairs in the same reported experiment. Later debugging requires a new evaluation round and a fresh untouched holdout.

Keep any known Python ports, AlphaTrans repaired translations, and answer-containing examples out of prompts, retrieval, and model-accessible directories. Public source contamination cannot be fully ruled out. Strengthen the evidence using freshly generated inputs and paired source variants: behavior-preserving renaming, and carefully reviewed behavior-changing mutations whose expected outputs are regenerated from the mutated Java source. This tests whether translation follows the actual supplied source rather than reproducing a memorized algorithm. Do not count many variants as independent repositories.

Property-based tests should enforce only properties valid for the exact API. For example, not every normalized string distance is a metric, and weighted variants may have different symmetry assumptions. Mutation tests can check whether the test suite detects representative bugs; they do not prove equivalence.

## 8. Metrics and interpretation

Pre-register the denominator of every rate and retain unvalidated outcomes.

- **Primary: all-tests-passing task rate.** Number of fixed benchmark tasks whose final candidate passes all required visible and withheld checks, divided by all admitted tasks. An eligible task with target setup failure, timeout, or unsupported verification does not count as success, but retains its own failure category.
- **Test-case parity rate.** Passing required cases divided by the fixed required case count. Report per task and macro-average across tasks; include planned cases that could not execute as non-passing in this operational measure. Also report counts for mismatch, execution failure, and unvalidated cases so the rate is not misread as pure semantic accuracy.
- **Validated-method fraction.** Methods exercised under the defined assertion-bearing validation protocol and passing all relevant required checks, divided by the fixed in-scope application-method count. Report isolated and integrated modes separately. Also report coverage and the covered-method denominator. A reached method alone is not a verified method.
- **First-pass execution rate.** Initial candidates that import and complete the designated smoke cases without unexpected execution errors, divided by admitted tasks. Report functional parity separately; merely running is weaker.
- **Repair/convergence.** First round passing the visible suite, final withheld performance, repair success among initial failures, and number of regressions. Report unresolved tasks and exhaustion separately; do not average only successful tasks and hide failures.
- **Cost.** Calls, input/output tokens, model cost where known, wall-clock time, environment provisioning time, execution time, and human setup effort. Report cold and cached provisioning separately when material.
- **Validation limitations.** Source instability, unsupported bridges/types, no assertion coverage, timeouts, and unknowns. Preserve total scope rather than silently dropping these outcomes.

Report absolute percentage-point improvements alongside raw counts. Use paired results by task/replicate and uncertainty estimates only at an appropriate grouping level. Methods in one library and generated cases from one method are correlated. With only one main library, descriptive paired outcomes and individual cases are more credible than broad statistical claims about all Java code.

Proposed practical target, to freeze before results: at least a 10-percentage-point improvement in primary task success over one-shot, within five repair rounds for a majority of initially failing tasks. This is a project goal, not a promised effect or a statistical significance criterion. A valid negative result remains useful. Call results test-supported behavioral parity rather than formal semantic equivalence.

## 9. Evidence now; diagnostic reports later

From the first run, save task/run/attempt IDs, source/candidate/environment hashes, commands and exit codes, stdout/stderr artifacts, test IDs, observed Java/Python values, exception data, relevant stack frames, patch diffs, test counts, timestamps, and resource usage. Save coverage where available. This is basic reproducibility infrastructure, not the deferred diagnostic research component.

The later report pipeline should deduplicate failures, identify the first relevant project frame, attach dependency/symbol context, separate observations from hypotheses, and propose a routing category. Each report assertion must point to an execution artifact. A hypothesis might be "integer division semantics differ"; the evidence should include the input, Java output, Python output, and source expression.

Begin with rule-based extraction from test/build outputs. Use an LLM summarizer only if it adds value, preserve raw evidence, and account for its cost. Evaluate raw versus structured reports on the same initial candidates, tests, and resources. Measure whether reports lead to verified repairs; plausibility of the prose is not a correctness measure.

## 10. Milestones, gates, and suggested ownership

These are original estimates for two contributors, not claims that all roadmap work is complete. At planning time, the workspace contained the five PDFs and no implementation; Docker and Maven were absent from the inspected PATH. The midpoint implementation now includes project-local Maven and a tested Java/GraalPy harness; see its handoff for the measured environment. The machine reports arm64. AlphaTrans's artifact notes an amd64 container option for Apple Silicon [W1]; reproducing that separate artifact remains future work.

### Milestone 0 — Freeze scope and validate source tasks (1–2 working days)

Both: agree on the pilot subset, CLI subject boundary, behavioral contract, candidate selection criteria, model access, and experiment budget. Ram: pin and build the Java subject. Vamsi: define task manifests and outcome records. Read artifact requirements and test AlphaTrans feasibility with a strictly limited setup budget.

Exit: stable Java test evidence, exact source IDs and selected methods, published planned denominators, and explicit supported/unsupported features. No model-generated translation yet.

### Milestone 1 — Establish the GraalPy and CPython harness (2–3 days)

Ram leads bridge/container work; Vamsi helps define comparators and evidence formats. Use a manually checked miniature fixture to exercise value conversion, exceptions, and supported state changes. Test a known-good and deliberately wrong candidate.

Exit: both Python execution paths are working, the wrong candidate is rejected, the target execution path is observable, and all evaluator inputs are immutable. If custom object bridging blocks progress, narrow supported interfaces and report that limitation; retain GraalPy validation for the supported pilot.

### Milestone 2 — Build one-shot translation (2–3 days)

Vamsi leads the model adapter, context assembly, source-to-target map, skeleton generation, and minimal knowledge pack. Ram wires the same harness around generated candidates. Audit required Java APIs and Python equivalents.

Exit: reproducible baseline candidate artifacts and raw execution/parity results. Do not tune against the main subject's withheld tests.

### Milestone 3 — Add controlled repair and environment routing (2–3 days)

Vamsi implements scoped patches and stopping/rollback policy. Ram implements permitted target-environment operations and regression execution. Build the fixed-environment and environment-aware arms from the same controller with explicit capability switches.

Exit: a real observed pilot failure can be repaired or cleanly classified within the limit; repeated/no-op failures terminate; all runs retain immutable tests and complete evidence. Record unresolved cases rather than forcing a successful demonstration.

### Milestone 4 — Freeze and run the main study (3–5 days, plus compute)

Both: finalize scope based on source/bridge feasibility, freeze the protocol, and run paired comparisons on CLI. Complete AlphaTrans comparison if the early feasibility gate succeeded. Include CPython integration checks and independent final inputs.

Exit: raw results for every planned task/arm/replicate, a reproducible aggregate, and a claim limited to the observed evidence. If setup blocked AlphaTrans, report the block and omit a superiority claim.

### Milestone 5 — Optional diagnostics, robustness, and expansion (remaining time)

Vamsi leads structured reports and failure taxonomy; Ram extends bridge or test coverage where justified. Compare structured versus raw feedback first; add retrieval ablations or another library only if enough time remains for a frozen, reproducible evaluation.

The proposal's November 20 endpoint leaves roughly a month from this plan's date. If that remains the deadline, prioritize milestones 0–4 and reserve the final week for analysis and writing. Existing work outside this workspace can shorten the schedule once inspected; the old proposal dates do not establish its completion.

## 11. Later generalization and automation

After the Java-to-Python experiment is stable, separate source-language analysis, target-language generation, runtime execution, bridge conversion, and observation comparison behind interfaces. Reuse the controller, artifact store, budgets, and reporting across language pairs. Keep language semantics and runtime adapters explicit; replacing a prompt is not sufficient to support a new language.

Then add resumable command-line runs, deterministic replay of saved model responses, CI execution on pinned images, and selective revalidation of changed dependency groups. Broader environment autonomy, arbitrary Java frameworks, concurrency, reflection/JNI, databases, and general cyclic object graphs remain outside the first study. Add them only as separately measured capabilities.

## 12. First implementation increment after this plan

Build one end-to-end evaluator case around a pinned Levenshtein API: run Java reference behavior, invoke a manually checked Python implementation via GraalPy, run the same implementation under CPython, and reject a deliberately wrong result. Persist the evidence and freeze the comparator. That establishes the verification path on which every later accuracy claim depends.

## Sources

Local PDF page numbers below are physical PDF pages, not necessarily publisher page labels.

- **[P1]** [AlphaTrans](./AlphaTrans.pdf). Especially pp. 1–3, 5–11, Table 2 on p. 13, bugs on p. 15, coverage on pp. 16–17, model ablation on p. 18, and threats on p. 20.
- **[P2]** [Environment-in-the-Loop: Rethinking Code Migration with LLM-based Agents](<./Environment in the loop paper.pdf>). Architecture and workflow, pp. 3–4; framing and limitations, pp. 1–4.
- **[P3]** [A Multi-Perspective Investigation into Code Migration for Large Language Models](./A_Multi-Perspective_Investigation_into_Code_Migrat.pdf). Survey and evaluation directions, pp. 5–10.
- **[P4]** [CS 6158 Project Proposal](<./CS 6158 Project Proposal (1).pdf>). Roles on p. 1; evaluation, timeline, and four candidate libraries on p. 2.
- **[P5]** [Java-to-Python presentation PDF](<./Environment-in-the-Loop Java-to-Python Migration (1) (1).pdf>). Motivation on slide 2; GraalVM on slides 3–4; pilot and comparison arms on slide 6.
- **[W1]** [AlphaTrans artifact repository](https://github.com/Intelligent-CAT-Lab/AlphaTrans). Read-only inspection of reproduction guidance and prepared-subject availability; no reproduction performed.
- **[W2]** [java-string-similarity upstream repository](https://github.com/tdebatty/java-string-similarity). Used to confirm pilot algorithm choices; no pinned-source build performed.
- **[W3]** [GraalPy documentation for JVM developers](https://graalpy.org/jvm-developers/docs/). Embedding and interoperability feasibility; exact runtime stack must be smoke-tested and pinned.
- **[W4]** [Java 21 String API](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/String.html). UTF-16 indexing contract.
- **[W5]** [Java Language Specification 21, string conversion](https://docs.oracle.com/javase/specs/jls/se21/html/jls-5.html#jls-5.1.11). Null string conversion.
- **[W6]** [Python 3.12 built-in types](https://docs.python.org/3.12/library/stdtypes.html#text-sequence-type-str). String/code-point semantics; actual target version will be pinned during setup.
