# Four-arm Validator study: frozen prospective protocol

Prepared November 22, 2026 local time. The live attempt stopped early; no completed factorial comparison.

Question: was the previous paired benefit driven by runtime capability diagnosis,
Java decimal semantic guidance, or their combination?

Four fresh initial Gemini 3.5 Flash translations are each shared across four arms:
ordinary visible-feedback repair, capability diagnosis only, Java semantic guidance
only, and both. Common source excerpts and visible failures are identical. Diagnosis
adds only API availability results; semantic guidance adds only the Java decimal
block contract. No deterministic rewrites or manual candidate edits are allowed.
Normal test failures may themselves reveal unavailable APIs; the intervention is
additional explicit probing, not removal of ordinary diagnostics from controls.

All arms receive at most one repair, 4,096 output tokens, low thinking, and the
same visible per-case no-regression selection gate. Arm order rotates so each arm
occupies each position once. The initial request is shared and billed once.
Initials passing all visible cases skip repair for every arm and remain included.

30 development cases are unchanged. Seed 2026112202 generates 136 new withheld
cases, disjoint in input values from the preceding paired study and development
suite, including new surrogate inputs and numeric boundaries. This is new input
coverage within known semantic strata, not independent semantic discovery. Java
oracle outcomes are repeated before generation. All selections freeze before
withheld candidate scoring; prompts never contain withheld cases.

Maximum: 20 requests (four initials plus sixteen repairs), 81,920 output tokens,
$1.60 accounting cap. Each request has its own $0.08 envelope; unused allowance
cannot transfer to another arm. Rates are declared estimates, not invoice prices.
Provider or budget failures stop the batch and are archived, not discarded.

Primary endpoint: full visible-plus-withheld success in both runtimes. Secondary:
case accuracy by runtime, accepted/rejected repairs, calls, tokens, cost and elapsed
time. Analyze within-trial contrasts: diagnosis-only minus ordinary, semantics-only
minus ordinary, and both versus each single treatment. Report interaction
(both - diagnosis-only - semantics-only + ordinary) descriptively on paired binary
outcomes. Four trials are exploratory; do not claim statistical superiority.

Reproduce preparation: `python3 scripts/validator_factorial_study.py` from midpoint.
Only `--live` makes requests and requires a separately approved study budget.
Preparation archives the plan, repeated Java oracle, frozen suite and diagnosis.
This protocol concerns Validator portability, not controlled infrastructure recovery
or cross-project replication. Those remain separate planned experiments.

## Attempt outcome

Preparation archive: `evidence/20261123T015853Z-validator-factorial-9dfc6acc`.
Live archive: `evidence/20261123T015934Z-validator-factorial-d7ae47bf`.
Both checksum inventories were verified. The study stopped in trial 0 on the
third request (diagnosis-only repair): the provider returned `MAX_TOKENS` and
incomplete code. Initial and ordinary-repair responses were recorded. No
withheld candidate scoring occurred; **0 complete comparisons**, not 0% accuracy.
The other three trials did not run. The predeclared stop policy was honored.

Usage: three requests, **13,893 tokens**, **$0.082835625 accounted**, **53.689
seconds**. The failed request itself consumed 6,484 tokens: 2,406 input and 4,078
output, including 3,440 thinking tokens. Thinking consumed much of its output
allowance; this is not evidence of an invalid API key or a translation accuracy
failure. No retry or token-cap increase occurred.

All **145 Python tests passed**, including treatment separation, fresh-input
checks, balanced order and incomplete-pair reporting. The machine-readable
report is `reports/validator-factorial.json`. Prior 0/3 versus 2/3 paired results
remain unchanged. A future protocol should predeclare incomplete-output handling
and either shorter generated modules or a revised output/thinking budget before
rerunning; do not remove this failed attempt or pool it with completed trials.
