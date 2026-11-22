"""Deterministic source compaction; no tests, candidates, or evaluator imports."""
import re

# Preserve Java literals before recognizing comments. Pinned CSV 1.10 has no text blocks.
TOKENS = re.compile(r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|//[^\n]*|/\*.*?\*/""", re.DOTALL)


def compact_java(source):
    def replace(match):
        value = match.group()
        return " " if value.startswith(("//", "/*")) else value
    return "\n".join(line.strip() for line in TOKENS.sub(replace, source).splitlines() if line.strip())


SEMANTIC_GUIDANCE = """SOURCE-GROUNDED IMPLEMENTATION CHECKLIST (not evaluation answers):
- Contract character settings use exactly one UTF-16 code unit. A supplementary Unicode
  code point occupies two units even when Python len returns one; reject it as
  IllegalArgumentException. Apply this to delimiter, quote and escape. None is only
  allowed for quote/escape. Booleans must be actual bool, not truthy strings or integers.
- Lexer.isEscapeDelimiter consumes escaped delimiters before Lexer.readEscape.
  readEscape maps r/n/t/b/f to control characters, accepts escaped literal controls
  and meta-characters, rejects terminal escape with IOException, and returns an
  unknown-escape sentinel. BOTH parseSimpleToken and parseEncapsulatedToken preserve
  the escape and following character for that sentinel. Do not use Python csv's
  escape behavior as an equivalent implementation without checking these branches.
- CSVParser.handleNull distinguishes quoted/unquoted fields in ALL_NON_NULL and
  NON_NUMERIC modes. Preserve that quoted flag until null handling is complete.
- Java String.trim removes code units <= U+0020; Character.isWhitespace differs
  from Python str.isspace (notably nonbreaking spaces). Preserve the distinct
  lexer surrounding-space and format trim operations.
- CSVFormat.printWithQuotes/printWithEscapes decide exact quoting, escaping and
  record separators. All non-null input cells in this contract are strings, even
  when they look numeric. Null handling is separate from empty strings.
Inspect the provided executable source for all branches; this checklist is not
an exhaustive specification. Build a coherent state machine rather than patching
individual examples. Review parse and print configuration validation together.
"""
