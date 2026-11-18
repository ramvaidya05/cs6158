import io
import numbers

class CSVParseError(Exception):
    pass

class IllegalArgumentException(Exception):
    pass

class QuoteMode:
    ALL = 'ALL'
    ALL_NON_NULL = 'ALL_NON_NULL'
    MINIMAL = 'MINIMAL'
    NON_NUMERIC = 'NON_NUMERIC'
    NONE = 'NONE'

    VALID_MODES = {ALL, ALL_NON_NULL, MINIMAL, NON_NUMERIC, NONE}

class _TokenType:
    INVALID = 'INVALID'
    TOKEN = 'TOKEN'
    EOF = 'EOF'
    EORECORD = 'EORECORD'
    COMMENT = 'COMMENT'

class _Token:
    def __init__(self):
        self.type = _TokenType.INVALID
        self.content = []
        self.is_ready = False
        self.is_quoted = False

    def reset(self):
        self.content.clear()
        self.type = _TokenType.INVALID
        self.is_ready = False
        self.is_quoted = False

    def get_content(self):
        return "".join(self.content)

class _ExtendedBufferedReader:
    UNDEFINED = -2
    END_OF_STREAM = -1

    def __init__(self, text: str):
        self.text = text
        self.length = len(text)
        self.idx = 0
        self.last_char = self.UNDEFINED
        self.eol_counter = 0
        self.position = 0
        self.closed = False

    def close(self):
        self.closed = True
        self.last_char = self.END_OF_STREAM

    def get_current_line_number(self):
        if self.last_char in (ord('\r'), ord('\n'), self.UNDEFINED, self.END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1

    def get_last_char(self):
        return self.last_char

    def get_position(self):
        return self.position

    def is_closed(self):
        return self.closed

    def look_ahead(self, n=1):
        if n == 1:
            if self.idx < self.length:
                return ord(self.text[self.idx])
            return self.END_OF_STREAM
        else:
            res = []
            for i in range(n):
                if self.idx + i < self.length:
                    res.append(self.text[self.idx + i])
                else:
                    break
            return res

    def read(self):
        if self.idx >= self.length:
            current = self.END_OF_STREAM
        else:
            current = ord(self.text[self.idx])
            self.idx += 1

        if (
            current == ord('\r')
            or (current == ord('\n') and self.last_char != ord('\r'))
            or (
                current == self.END_OF_STREAM
                and self.last_char != ord('\r')
                and self.last_char != ord('\n')
                and self.last_char != self.END_OF_STREAM
            )
        ):
            self.eol_counter += 1

        self.last_char = current
        self.position += 1
        return self.last_char

    def read_chars(self, n):
        if n == 0:
            return []
        buf = []
        for _ in range(n):
            c = self.read()
            if c == self.END_OF_STREAM:
                break
            buf.append(chr(c))
        return buf

    def read_line(self):
        if self.look_ahead() == self.END_OF_STREAM:
            return None
        buffer = []
        while True:
            current = self.read()
            if current == ord('\r'):
                next_c = self.look_ahead()
                if next_c == ord('\n'):
                    self.read()
            if current in (self.END_OF_STREAM, ord('\n'), ord('\r')):
                break
            buffer.append(chr(current))
        return "".join(buffer)

class _CSVFormat:
    def __init__(self, config=None):
        if config is None:
            config = {}
        elif not isinstance(config, dict):
            raise IllegalArgumentException("Config must be a dictionary")

        def check_bool(name, default):
            if name in config:
                val = config[name]
                if not isinstance(val, bool):
                    raise IllegalArgumentException(f"{name} must be a boolean")
                return val
            return default

        self.delimiter = config.get("delimiter", ",")
        self.quote_character = config.get("quote", '"')
        self.escape_character = config.get("escape", None)
        self.record_separator = config.get("record_separator", "\r\n")
        self.null_string = config.get("null_string", None)
        self.quote_mode = config.get("quote_mode", None)
        self.ignore_empty_lines = check_bool("ignore_empty_lines", True)
        self.ignore_surrounding_spaces = check_bool("ignore_surrounding_spaces", False)
        self.trim = check_bool("trim", False)
        self.comment_marker = config.get("comment_marker", None)
        self.trailing_delimiter = check_bool("trailing_delimiter", False)
        self.headers = config.get("headers", None)
        self.skip_header_record = check_bool("skip_header_record", False)
        self.allow_missing_column_names = check_bool("allow_missing_column_names", False)
        self.duplicate_header_mode = config.get("duplicate_header_mode", "ALLOW_ALL")
        self.ignore_header_case = check_bool("ignore_header_case", False)

        self.validate()

    def validate(self):
        if self.delimiter is None:
            raise IllegalArgumentException("The delimiter cannot be null")
        if not isinstance(self.delimiter, str):
            raise IllegalArgumentException("The delimiter must be a string")
        if len(self.delimiter) == 0:
            raise IllegalArgumentException("The delimiter cannot be empty")
        if "\r" in self.delimiter or "\n" in self.delimiter:
            raise IllegalArgumentException("The delimiter cannot be a line break")

        if self.quote_character is not None:
            if not isinstance(self.quote_character, str) or len(self.quote_character) != 1:
                raise IllegalArgumentException("Quote must be one character")
            if self.quote_character in self.delimiter:
                raise IllegalArgumentException("The quoteChar character and the delimiter cannot be the same")
            if self.quote_character in ("\r", "\n"):
                raise IllegalArgumentException("The quoteChar cannot be a line break")

        if self.escape_character is not None:
            if not isinstance(self.escape_character, str) or len(self.escape_character) != 1:
                raise IllegalArgumentException("Escape must be one character")
            if self.escape_character in self.delimiter:
                raise IllegalArgumentException("The escape character and the delimiter cannot be the same")
            if self.escape_character in ("\r", "\n"):
                raise IllegalArgumentException("The escape character cannot be a line break")

        if self.comment_marker is not None:
            if not isinstance(self.comment_marker, str) or len(self.comment_marker) != 1:
                raise IllegalArgumentException("Comment marker must be one character")
            if self.comment_marker in self.delimiter:
                raise IllegalArgumentException("The comment start character and the delimiter cannot be the same")
            if self.comment_marker in ("\r", "\n"):
                raise IllegalArgumentException("The comment start marker character cannot be a line break")
            if self.quote_character is not None and self.quote_character == self.comment_marker:
                raise IllegalArgumentException("The comment start character and the quoteChar cannot be the same")
            if self.escape_character is not None and self.escape_character == self.comment_marker:
                raise IllegalArgumentException("The comment start and the escape character cannot be the same")

        if self.quote_mode is not None:
            if self.quote_mode not in QuoteMode.VALID_MODES:
                raise IllegalArgumentException(f"Unknown quote mode: {self.quote_mode}")

        if self.escape_character is None and self.quote_mode == QuoteMode.NONE:
            raise IllegalArgumentException("No quotes mode set but no escape character is set")

class _Lexer:
    DISABLED = "\ufffe"

    def __init__(self, format_spec: _CSVFormat, reader: _ExtendedBufferedReader):
        self.format = format_spec
        self.reader = reader
        self.delimiter = [ord(c) for c in format_spec.delimiter]
        self.delimiter_str = format_spec.delimiter
        self.escape = ord(format_spec.escape_character) if format_spec.escape_character else ord(self.DISABLED)
        self.quote_char = ord(format_spec.quote_character) if format_spec.quote_character else ord(self.DISABLED)
        self.comment_start = ord(format_spec.comment_marker) if format_spec.comment_marker else ord(self.DISABLED)
        self.ignore_surrounding_spaces = format_spec.ignore_surrounding_spaces
        self.ignore_empty_lines = format_spec.ignore_empty_lines
        self.first_eol = None
        self.is_last_token_delimiter = False

    def get_character_position(self):
        return self.reader.get_position()

    def get_current_line_number(self):
        return self.reader.get_current_line_number()

    def is_closed(self):
        return self.reader.is_closed()

    def is_comment_start(self, ch):
        return ch == self.comment_start

    def is_delimiter(self, ch):
        self.is_last_token_delimiter = False
        if ch != self.delimiter[0]:
            return False
        if len(self.delimiter) == 1:
            self.is_last_token_delimiter = True
            return True
        n = len(self.delimiter) - 1
        ahead = self.reader.look_ahead(n)
        if len(ahead) < n:
            return False
        for i in range(n):
            if ord(ahead[i]) != self.delimiter[i + 1]:
                return False
        chars = self.reader.read_chars(n)
        self.is_last_token_delimiter = len(chars) == n
        return self.is_last_token_delimiter

    def is_end_of_file(self, ch):
        return ch == _ExtendedBufferedReader.END_OF_STREAM

    def is_escape(self, ch):
        return ch == self.escape

    def is_escape_delimiter(self):
        expected_len = 2 * len(self.delimiter) - 1
        ahead = self.reader.look_ahead(expected_len)
        if len(ahead) < expected_len:
            return False
        if ord(ahead[0]) != self.delimiter[0]:
            return False
        for i in range(1, len(self.delimiter)):
            if ord(ahead[2 * i]) != self.delimiter[i] or ord(ahead[2 * i - 1]) != self.escape:
                return False
        chars = self.reader.read_chars(expected_len)
        return len(chars) == expected_len

    def is_meta_char(self, ch):
        return ch in (self.escape, self.quote_char, self.comment_start)

    def is_quote_char(self, ch):
        return ch == self.quote_char

    def is_start_of_line(self, ch):
        return ch in (ord('\n'), ord('\r'), _ExtendedBufferedReader.UNDEFINED)

    def next_token(self, token: _Token):
        last_char = self.reader.get_last_char()
        c = self.reader.read()
        eol = self.read_end_of_line(c)

        if self.ignore_empty_lines:
            while eol and self.is_start_of_line(last_char):
                last_char = c
                c = self.reader.read()
                eol = self.read_end_of_line(c)
                if self.is_end_of_file(c):
                    token.type = _TokenType.EOF
                    return token

        if self.is_end_of_file(last_char) or (not self.is_last_token_delimiter and self.is_end_of_file(c)):
            token.type = _TokenType.EOF
            return token

        if self.is_start_of_line(last_char) and self.is_comment_start(c):
            line = self.reader.read_line()
            if line is None:
                token.type = _TokenType.EOF
                return token
            comment = line.strip()
            token.content.extend(comment)
            token.type = _TokenType.COMMENT
            return token

        while token.type == _TokenType.INVALID:
            if self.ignore_surrounding_spaces:
                while c != _ExtendedBufferedReader.END_OF_STREAM and chr(c).isspace() and not self.is_delimiter(c) and not eol:
                    c = self.reader.read()
                    eol = self.read_end_of_line(c)

            if self.is_delimiter(c):
                token.type = _TokenType.TOKEN
            elif eol:
                token.type = _TokenType.EORECORD
            elif self.is_quote_char(c):
                self.parse_encapsulated_token(token)
            elif self.is_end_of_file(c):
                token.type = _TokenType.EOF
                token.is_ready = True
            else:
                self.parse_simple_token(token, c)

        return token

    def parse_encapsulated_token(self, token: _Token):
        token.is_quoted = True
        start_line_number = self.get_current_line_number()
        while True:
            c = self.reader.read()
            if self.is_escape(c):
                if self.is_escape_delimiter():
                    token.content.extend(self.delimiter_str)
                else:
                    unescaped = self.read_escape()
                    if unescaped == _ExtendedBufferedReader.END_OF_STREAM:
                        token.content.append(chr(c))
                        token.content.append(chr(self.reader.get_last_char()))
                    else:
                        token.content.append(chr(unescaped))
            elif self.is_quote_char(c):
                if self.is_quote_char(self.reader.look_ahead()):
                    c = self.reader.read()
                    token.content.append(chr(c))
                else:
                    while True:
                        c = self.reader.read()
                        if self.is_delimiter(c):
                            token.type = _TokenType.TOKEN
                            return token
                        if self.is_end_of_file(c):
                            token.type = _TokenType.EOF
                            token.is_ready = True
                            return token
                        if self.read_end_of_line(c):
                            token.type = _TokenType.EORECORD
                            return token
                        if not (c != _ExtendedBufferedReader.END_OF_STREAM and chr(c).isspace()):
                            raise CSVParseError(
                                f"(line {self.get_current_line_number()}) invalid char between encapsulated token and delimiter"
                            )
            elif self.is_end_of_file(c):
                raise CSVParseError(
                    f"(startline {start_line_number}) EOF reached before encapsulated token finished"
                )
            else:
                token.content.append(chr(c))

    def parse_simple_token(self, token: _Token, ch: int):
        while True:
            if self.read_end_of_line(ch):
                token.type = _TokenType.EORECORD
                break
            if self.is_end_of_file(ch):
                token.type = _TokenType.EOF
                token.is_ready = True
                break
            if self.is_delimiter(ch):
                token.type = _TokenType.TOKEN
                break

            if self.is_escape(ch):
                if self.is_escape_delimiter():
                    token.content.extend(self.delimiter_str)
                else:
                    unescaped = self.read_escape()
                    if unescaped == _ExtendedBufferedReader.END_OF_STREAM:
                        token.content.append(chr(ch))
                        token.content.append(chr(self.reader.get_last_char()))
                    else:
                        token.content.append(chr(unescaped))
            else:
                token.content.append(chr(ch))
            ch = self.reader.read()

        if self.ignore_surrounding_spaces:
            self.trim_trailing_spaces(token.content)

        return token

    def read_end_of_line(self, ch: int):
        if ch == ord('\r') and self.reader.look_ahead() == ord('\n'):
            ch = self.reader.read()
            if self.first_eol is None:
                self.first_eol = "\r\n"
        if self.first_eol is None:
            if ch == ord('\n'):
                self.first_eol = "\n"
            elif ch == ord('\r'):
                self.first_eol = "\r"
        return ch in (ord('\n'), ord('\r'))

    def read_escape(self):
        ch = self.reader.read()
        if ch == ord('r'):
            return ord('\r')
        elif ch == ord('n'):
            return ord('\n')
        elif ch == ord('t'):
            return ord('\t')
        elif ch == ord('b'):
            return ord('\b')
        elif ch == ord('f'):
            return ord('\f')
        elif ch in (ord('\r'), ord('\n'), ord('\f'), ord('\t'), ord('\b')):
            return ch
        elif ch == _ExtendedBufferedReader.END_OF_STREAM:
            raise CSVParseError("EOF whilst processing escape sequence")
        else:
            if self.is_meta_char(ch):
                return ch
            return _ExtendedBufferedReader.END_OF_STREAM

    def trim_trailing_spaces(self, buffer):
        while buffer and buffer[-1].isspace():
            buffer.pop()


def parse_csv(text: str, config: dict = None):
    fmt = _CSVFormat(config)
    reader = _ExtendedBufferedReader(text)
    lexer = _Lexer(fmt, reader)
    reusable_token = _Token()
    record_list = []
    records = []

    def is_strict_quote_mode():
        return fmt.quote_mode in (QuoteMode.ALL_NON_NULL, QuoteMode.NON_NUMERIC)

    def handle_null(input_str: str):
        is_quoted = reusable_token.is_quoted
        null_string = fmt.null_string
        strict = is_strict_quote_mode()
        if input_str == null_string:
            return input_str if (strict and is_quoted) else None
        if strict and null_string is None and input_str == "" and not is_quoted:
            return None
        return input_str

    def add_record_value(last_record: bool):
        raw = reusable_token.get_content()
        val = raw.strip() if fmt.trim else raw
        if last_record and val == "" and fmt.trailing_delimiter:
            return
        record_list.append(handle_null(val))

    while True:
        record_list.clear()
        while True:
            reusable_token.reset()
            lexer.next_token(reusable_token)
            if reusable_token.type == _TokenType.TOKEN:
                add_record_value(False)
            elif reusable_token.type == _TokenType.EORECORD:
                add_record_value(True)
                break
            elif reusable_token.type == _TokenType.EOF:
                if reusable_token.is_ready:
                    add_record_value(True)
                break
            elif reusable_token.type == _TokenType.INVALID:
                raise CSVParseError(f"(line {lexer.get_current_line_number()}) invalid parse sequence")
            elif reusable_token.type == _TokenType.COMMENT:
                reusable_token.type = _TokenType.TOKEN
            else:
                raise CSVParseError(f"Unexpected Token type: {reusable_token.type}")

        if record_list:
            records.append(list(record_list))
        else:
            if reusable_token.type == _TokenType.EOF:
                break

    return records

def _is_trim_char(c: str) -> bool:
    return ord(c) <= ord(' ')

def _trim_char_sequence(s: str) -> str:
    pos = 0
    length = len(s)
    while pos < length and _is_trim_char(s[pos]):
        pos += 1
    while pos < length and _is_trim_char(s[length - 1]):
        length -= 1
    return s[pos:length]

def _is_delimiter_at(char_seq: str, start_index: int, delim: str) -> bool:
    if not delim:
        return False
    if char_seq[start_index] != delim[0]:
        return False
    delim_len = len(delim)
    if start_index + delim_len > len(char_seq):
        return False
    return char_seq[start_index:start_index + delim_len] == delim

def _print_with_escapes(char_seq: str, out: io.StringIO, delimiter: str, escape_char: str):
    pos = 0
    start = 0
    end = len(char_seq)
    delim_len = len(delimiter)

    while pos < end:
        c = char_seq[pos]
        is_delim_start = _is_delimiter_at(char_seq, pos, delimiter)
        if c in ('\r', '\n', escape_char) or is_delim_start:
            if pos > start:
                out.write(char_seq[start:pos])
            if c == '\n':
                c = 'n'
            elif c == '\r':
                c = 'r'

            out.write(escape_char)
            out.write(c)

            if is_delim_start:
                for _ in range(1, delim_len):
                    pos += 1
                    c = char_seq[pos]
                    out.write(escape_char)
                    out.write(c)

            start = pos + 1
        pos += 1

    if pos > start:
        out.write(char_seq[start:pos])

def _print_with_quotes(
    obj,
    char_seq: str,
    out: io.StringIO,
    new_record: bool,
    delimiter: str,
    quote_char: str,
    escape_char: str,
    quote_mode: str,
):
    quote = False
    pos = 0
    start = 0
    length = len(char_seq)
    eff_escape_char = escape_char if escape_char is not None else quote_char
    quote_policy = quote_mode if quote_mode is not None else QuoteMode.MINIMAL

    if quote_policy in (QuoteMode.ALL, QuoteMode.ALL_NON_NULL):
        quote = True
    elif quote_policy == QuoteMode.NON_NUMERIC:
        is_num = isinstance(obj, numbers.Number) and not isinstance(obj, bool)
        quote = not is_num
    elif quote_policy == QuoteMode.NONE:
        _print_with_escapes(char_seq, out, delimiter, escape_char)
        return
    elif quote_policy == QuoteMode.MINIMAL:
        if length <= 0:
            if new_record:
                quote = True
        else:
            c = char_seq[0]
            if ord(c) <= ord('#'):
                quote = True
            else:
                while pos < length:
                    c = char_seq[pos]
                    if (
                        c in ('\n', '\r', quote_char, eff_escape_char)
                        or _is_delimiter_at(char_seq, pos, delimiter)
                    ):
                        quote = True
                        break
                    pos += 1

                if not quote:
                    last_c = char_seq[length - 1]
                    if _is_trim_char(last_c):
                        quote = True

        if not quote:
            out.write(char_seq)
            return
    else:
        raise IllegalArgumentException("Unexpected Quote value: " + str(quote_policy))

    if not quote:
        out.write(char_seq)
        return

    out.write(quote_char)
    pos = 0
    start = 0
    while pos < length:
        c = char_seq[pos]
        if c in (quote_char, eff_escape_char):
            out.write(char_seq[start:pos])
            out.write(eff_escape_char)
            start = pos
        pos += 1
    out.write(char_seq[start:pos])
    out.write(quote_char)

def print_csv(records, config: dict = None) -> str:
    fmt = _CSVFormat(config)
    out = io.StringIO()

    def print_val(val, new_record: bool):
        if val is None:
            if fmt.null_string is None:
                char_sequence = ""
            elif fmt.quote_mode == QuoteMode.ALL:
                q = fmt.quote_character if fmt.quote_character else ""
                char_sequence = q + fmt.null_string + q
            else:
                char_sequence = fmt.null_string
        elif isinstance(val, str):
            char_sequence = val
        else:
            char_sequence = str(val)

        if fmt.trim:
            char_sequence = _trim_char_sequence(char_sequence)

        if not new_record:
            out.write(fmt.delimiter)

        if val is None:
            out.write(char_sequence)
        elif fmt.quote_character is not None:
            _print_with_quotes(
                val,
                char_sequence,
                out,
                new_record,
                fmt.delimiter,
                fmt.quote_character,
                fmt.escape_character,
                fmt.quote_mode,
            )
        elif fmt.escape_character is not None:
            _print_with_escapes(char_sequence, out, fmt.delimiter, fmt.escape_character)
        else:
            out.write(char_sequence)

    for record in records:
        first = True
        for val in record:
            print_val(val, first)
            first = False
        if fmt.trailing_delimiter:
            out.write(fmt.delimiter)
        if fmt.record_separator is not None:
            out.write(fmt.record_separator)

    return out.getvalue()
