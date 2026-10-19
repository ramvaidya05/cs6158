# Midpoint evidence

`20261019T214029Z-verification-1aee5b7b/` is the completed acceptance archive.
Its summary records three synthetic replay tasks, 138 task/case combinations,
276 passing final runtime checks, and five passing upstream JUnit test methods.
`unit-tests.json` records all 33 passing Python tests. Per-task directories hold
the prompts, candidates, reference outputs, execution logs, and comparisons.

These results validate the harness, not LLM translation performance. The initial
candidate was deliberately broken and the replacement fixtures were hand-authored.
The public withheld split was excluded from repair prompts but is not a private
research evaluation set.

`setup-failure-graal-cache/` preserves an earlier real infrastructure failure.
It is separate from the successful acceptance results and is not scored as a
translation failure.

Reproduce with `python3 scripts/bootstrap.py` followed by
`python3 scripts/verify.py --archive` from the project root. Each invocation makes
a new archive; retain prior evidence unchanged. Absolute paths in historical
logs describe the machine used for that run and are not portable configuration.
