# Retry memory and Commons CLI v3 observations

Date: November 17, 2026. This checkpoint implements trial-local retry history, pruned diagnostics, dependency proposals, and the expanded CLI evaluator. Validation uses unit tests, the Java reference, and synthetic Docker replays. No fresh Gemini calls were made for this checkpoint.

## Retry feedback and memory

`--retry-memory` enables pruned feedback and a separate history for each main-study repair arm. `--memory-ablation` instead selects `one_shot`, `memory_off`, and `memory_on`, with identical pruned current feedback and equal repair limits in the two repair arms. Memory and feedback ablations cannot be combined. Existing default arms retain their existing feedback; memory is opt-in so it does not silently change the treatment.

Each enabled arm writes `TRANSLATION_FAILURES.md` and machine-readable `translation_failures.json`. Entries identify the attempted candidate, visible failure evidence, accepted/rejected checkpoint, bounded code-revision excerpt, and previously failing observations that now pass. They do not infer a root cause or claim a verified general fix. Rejected attempts remain in history, while the next repair starts from the best non-regressing checkpoint.

Pruned feedback groups duplicate observations, caps representative groups, shows the first mismatching operation with a bounded operation prefix and expected/actual values, and retains relevant candidate traceback locations. Complete evaluation logs remain in the archive. Model memory is bounded (recent excerpts, up to 16,000 characters); full history remains on disk. Candidate output is treated as data. This is prompt context, not model training or cross-trial learning.

Memory is instantiated inside each run directory and is never loaded from another trial or arm. Only visible summaries update it. All paired selections freeze before holdout scoring, and no memory updates occur during holdout evaluation. Existing stop rules remain: visible pass, repeated candidate, two non-improving revisions, retry limit, and resource limits.

## Requirements generation and limits

Every attempt and selected candidate receives `requirements.txt` and `dependencies.json`. AST inspection identifies imports without executing the candidate. Standard-library imports need no pip entries. Third-party and relative imports are reported as unresolved; dynamic-loading constructs recognized by the static check are also blocked. Syntax failures retain their separate classification.

**The current approved third-party package set is empty.** The existing CLI contract requires a standalone module using only the standard library. Thus generated requirements files are intentionally empty apart from an explanatory comment. Unsupported dependencies produce repair feedback before candidate execution, rather than guessed distribution names or automatic network installation. This is not a general package resolver and static inspection is not a security sandbox; Docker remains the execution boundary. Standard-library module availability still requires validation in both runtimes.

Third-party installation has not been enabled: it would require reviewed import-to-distribution mappings, pinned packages, artifacts compatible with both runtimes, and new reproducible container images. No dependency installation or package download is needed for this CLI slice. Do not describe this checkpoint as supporting arbitrary LLM-generated requirements.

## Expanded benchmark

`commons-cli-extended-v3` exposes 32 methods and four constructors across five classes. New scope includes OptionGroup membership, selection/conflicts, required groups, parser reuse, option descriptions, argument names, optional arguments, arity, and matching long options.

The frozen suite has 44 visible and 28 holdout scenarios. Repeated Java reference executions match. The executable audit finds **32/32 methods with normal-return observations in each split**, closing the previous five-method holdout gap. This is API exercise, not branch coverage or proof of complete semantic equivalence. Group-name collections are sorted by the adapters because source collection order is unspecified; required group entries preserve canonical object handles.

The result meets the plan's approximate 30–60 scored-method scope target. It remains one Python module and a selected CLI API, not arbitrary repository translation. Help formatting, Properties defaults, typed conversion, and unrestricted object graphs remain excluded.

The contract and adapters changed, so old suites must not be run under the new evaluator as if the protocols were identical. Archived studies were not rewritten. Reproducing them requires their recorded source version and evaluator fingerprints. New v3 studies must be reported separately.

## Local validation

- 101 Python unit tests and five Java tests passed at this checkpoint.
- Both Docker candidate images were rebuilt from the changed contract/adapters.
- The synthetic qualification baseline passes all 44 visible scenarios on each runtime (88/88 observations across CPython and GraalPy).
- All 16 injected mutations were detected on both runtimes using newly failing baseline-passing visible cases. Evidence: `evidence/20261117T231537Z-cli-semantic-qualification-3c3df280`.
- Paired synthetic memory replay: one-shot 82/88 visible and 48/56 holdout; each repair arm improved 82 → 86 → 88 visible observations in two repairs and finished 56/56 holdout. Both arms received the same initial code. Evidence: `evidence/20261117T231651Z-experiment-555a5519`.
- The replay returned exit code 1 because its deliberately faulty one-shot arm failed, not because orchestration failed. All three arms completed.
- Artifact audit confirmed memory only in the enabled arm, no memory in initial prompts, no holdout case IDs in prompts/history, three recorded memory attempts, and zero model calls. Report, frozen suite, scope audit, and build/test logs: `evidence/20261117-retry-memory-v3-report`.
- The default CLI demo replay now points to labeled v3-compatible fixtures; the old fixture files are retained for historical unit checks.

The qualification baseline combines a previously archived Gemini response with explicitly labeled hand-written additions. The replay deliberately introduces faults and supplies predetermined repairs. Neither can measure whether memory improves Gemini's decisions; they test evaluator sensitivity and orchestration only.

## Subsequent live study

The authorized live smoke, main study, and memory ablation have now completed. See [CLI_V3_LIVE_OBSERVATIONS.md](CLI_V3_LIVE_OBSERVATIONS.md). The local validation results above remain explicitly synthetic.

## Live-study protocol guidance

Use the new suite and declare trial count, maximum retries (start with three), token/time allowances, and sufficient partitioned spend capacity before calling Gemini. Main-study arms and the memory ablation answer different questions and should remain separate. Do not pool v3 scores with v2 scores. No spend cap was raised automatically in this checkpoint.
