# Resolved GraalPy setup failure

These unmodified JSON files were copied from the first Levenshtein smoke run,
`runs/20261019T213435Z-smoke-1f3d7a1a/check/graal/`. GraalPy execution failed with
`ModuleNotFoundError: No module named 'json'` and resource-path warnings. The same
candidate passed all 26 visible cases in CPython.

Inspection confirmed the `python-resources` jar was on the classpath. Adding
`-Dpolyglot.engine.userResourceCache=<project>/.cache/graalvm` to the Java command
made GraalPy work in this restricted development environment. Later complete
acceptance runs pass in both runtimes. No candidate change was needed to resolve
this infrastructure failure.

The setting uses GraalVM's supported
[internal resource-cache configuration](https://www.graalvm.org/latest/reference-manual/embed-languages/).
The runner now performs a trusted preflight before any model generation.
