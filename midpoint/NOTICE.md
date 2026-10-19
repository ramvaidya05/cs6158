# Third-party source and derivative fixtures

The Java pilot sources, interfaces, and upstream tests are unmodified files from
Thibault Debatty's `java-string-similarity`, pinned by
`vendor/java-string-similarity/SOURCE.json`. Their MIT license and copyright notice
are reproduced in `vendor/java-string-similarity/LICENSE.md` and must accompany
redistribution. The hand-authored Python algorithm fixtures in `fixtures/` are
derived from that source and are covered by the same upstream notice.

Maven and runtime dependencies are downloaded separately into ignored local
directories. Each dependency retains its own license. The research PDFs are
unchanged and are not bundled into the executable project.
