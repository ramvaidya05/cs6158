# Commons Validator Luhn pilot — November 21, 2026

Scope: Apache Commons Validator 1.9.0 `LuhnCheckDigit.calculate` and `isValid`,
including inherited modulus behavior. This is not full-library translation.
Pinned Maven source, license, notice and hashes are in `vendor/commons-validator`;
the Java oracle uses the matching Maven binary. Inputs are strings or null;
calculate returns a string or normalized CheckDigitException, isValid a boolean.
Exact exception messages and arbitrary non-string inputs are outside this contract.

## Protocol

One live Gemini 3.5 Flash trial, low thinking, initial plus at most one repair.
Caps: two requests, 4,096 output tokens/request, 40,000 conservative token
reservations, $0.15 accounting limit. Frozen seed 6158: 30 visible and 130
withheld cases. Both oracle executions agreed before generation. Cases include
null/empty/zero codes, known examples, random decimal strings, invalid characters,
Unicode and supplementary digits, whitespace and a 1,000-character boundary.
Generated code executes only in isolated CPython and GraalPy containers.
Repair prompts contain source, prior candidate and visible failures only.
A repair must preserve every previously passing visible case in both runtimes
and improve at least one to replace the baseline. Holdout scoring follows selection.

## Observed results

| Candidate | CPython visible | GraalPy visible | CPython holdout | GraalPy holdout |
|---|---:|---:|---:|---:|
| Initial / selected | 28/30 | 28/30 | 126/130 | 126/130 |
| Proposed repair (rejected) | 30/30 | 10/30 | Not scored | Not scored |

Selected holdout accuracy is **96.92% in each runtime**; full-task success is
**0/1 trial**. The repair uses `unicodedata.decimal`, unavailable in the pinned
GraalPy runtime, causing regression. Initial failures concern Unicode decimal
digits. No manual candidate changes were made and no extra requests were sent.
The two runtime scores are correlated evaluations, not independent trials.
This is not a matched comparison with CLI, CSV, or Codec cohorts.

Usage: **7,596 total tokens** (3,344 input, 4,252 output including 2,264 thinking),
**38.122 seconds**, **$0.044538 conservatively accounted** at declared input/output
rates $1.50/$9.00 per million and the harness input premium; not a provider invoice.

Evidence: `evidence/20261121T232609Z-validator-luhn-pilot` contains the frozen
suite, source manifest, prompts, responses, both candidates, scores, usage and
checksums. All **131 Python tests passed**, including new boolean-return, null,
exception-normalization and prompt-separation checks; Java bootstrap and both
container builds succeeded. Existing library dispatch branches were preserved.

## Reproduction and next step

From `midpoint/`, run `python3 scripts/bootstrap.py`, then
`python3 scripts/build_containers.py`. `python3 scripts/validator_luhn_pilot.py
--prepare-only` freezes the oracle without model calls. Running without that flag
makes bounded live requests using the locally configured Gemini credentials.

At the initial pilot checkpoint, Validator was **not completed**. The subsequent
runtime diagnosis and assisted qualification are recorded below; the failed
trial remains unchanged.
Future scored studies need fresh independent holdout inputs, since these results
are now inspected. No additional spend is implied by this report.

## Runtime-aware continuation

A separately approved continuation adds a trusted, bounded diagnosis step in
`migration_lab/runtime_diagnosis.py`. It probes `unicodedata.category`, `decimal`,
and `digit` in both isolated runtimes. CPython supports all three; the pinned
GraalPy supports category but lacks decimal and digit. A Java source-launcher
probe exhaustively checks all 65,536 char values and verifies that the accepted
decimal characters form 37 blocks of ten. The diagnostic reports block bases,
not evaluation inputs. The model can use these to avoid unavailable APIs.

`python3 scripts/validator_runtime_repair.py` prepares and archives the diagnosis
without API calls; `--live` permits exactly one separately authorized repair.
The continuation retains the existing per-case, cross-runtime no-regression gate.
It archives preparation or failure even if diagnosis or generation fails. Its
previously evaluated holdout cases are explicitly labeled regression evidence.
This is a continuation with supplied runtime guidance, not an independent trial
or evidence that environment repair outperforms ordinary repair generally.

The live continuation was rejected: CPython visible 30/30, GraalPy visible
10/30. The model again called the missing decimal API despite explicit diagnosis.
Selected regression scores remained 126/130 in both runtimes. This call used
5,459 tokens (2,753 input; 2,706 output including thinking), 31.602 seconds and
$0.029515875 accounted. Archive:
`evidence/20261121T233614Z-validator-runtime-repair-d8f3e047`.

## Assisted qualification — November 22, 2026 local time

`scripts/validator_portability_fix.py` applies a deterministic AST transformation
to the archived continuation candidate. It replaces exactly one eligible
one-argument `unicodedata.decimal` call with a Java-compatible helper using the
verified decimal bases. Unsupported signatures, absent calls, helper-name
collisions and missing diagnosis fail closed. This is an engineered,
developer-assisted code repair, not successful autonomous model repair.

The selected implementation in `translations/commons_validator_luhn.py` passed
**30/30 visible and 130/130 regression cases in each isolated runtime**:
**160/160 per runtime (100%)**. All **135 Python tests passed**. Qualification
made **zero model calls**. Evidence:
`evidence/20261123T014432Z-validator-assisted-qualification-a93ae90f`
(archive identifier is UTC, November 22 local time).

Total Validator live usage across the pilot and continuation: **13,055 tokens**
and **$0.074053875 accounted**, below the aggregate $0.15 limit. Failed model
candidates remain archived. The supported Luhn slice passes the present contract;
this does not establish full Commons Validator completion or equivalence on every
possible input. Previously inspected holdout cases are regression evidence, not
fresh generalization evidence. The Java mapping probe verifies the diagnostic
contract; it is not an exhaustive end-to-end Luhn input test.

Next: freeze a fresh versioned evaluation suite before any new scored study,
including isolated surrogate inputs and broader string boundaries; compare
runtime diagnosis and deterministic remediation against ordinary code repair.
No further API requests are authorized by this report.
