import io
import numbers


class CSVParseError(Exception):
    """Raised when CSV parsing encounters an I/O or syntax error."""
    pass


class IllegalArgumentException(Exception):
    """Raised when configuration parameters are invalid or inconsistent."""
    pass


CR = "\r"
LF = "\n"
CRLF = "\r\n"
COMMENT = "#"
SP = " "
TAB = "\t"
BACKSPACE = "\b"
FF = "\f"
END_OF_STREAM = -1
UNDEFINED = -2
DISABLED = "\ufffe"

VALID_QUOTE_MODES = {"ALL", "ALL_NON_NULL", "MINIMAL", "NON_NUMERIC", "NONE"}


class Token:
    INVALID = 0
    TOKEN = 1
    EOF = 2
    EORECORD = 3
    COMMENT = 4

    def __init__(self):
        self.type = self.INVALID
        self.content = []
        self.is_ready = False
        self.is_quoted = False

    def reset(self):
        self.content.clear()
        self.type = self.INVALID
        self.is_ready = False
        self.is_quoted = False


class ExtendedBufferedReader:
    def __init__(self, text):
        self.text = text
        self.length = len(text)
        self.position = 0
        self.read_cursor = 0
        self.last_char = UNDEFINED
        self.eol_counter = 0
        self.closed = False

    def close(self):
        self.closed = True
        self.last_char = END_OF_STREAM

    def is_closed(self):
        return self.closed

    def get_current_line_number(self):
        if self.last_char in (ord(CR), ord(LF), UNDEFINED, END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1

    def get_last_char(self):
        return self.last_char

    def get_position(self):
        return self.position

    def look_ahead(self):
        if self.read_cursor < self.length:
            return ord(self.text[self.read_cursor])
        return END_OF_STREAM

    def look_ahead_n(self, n):
        end = min(self.length, self.read_cursor + n)
        return [ord(c) for c in self.text[self.read_cursor:end]]

    def read(self):
        if self.read_cursor >= self.length:
            current = END_OF_STREAM
        else:
            current = ord(self.text[self.read_cursor])
            self.read_cursor += 1

        if (current == ord(CR) or
                (current == ord(LF) and self.last_char != ord(CR)) or
                (current == END_OF_STREAM and self.last_char not in (ord(CR), ord(LF), END_OF_STREAM))):
            self.eol_counter += 1

        self.last_char = current
        self.position += 1
        return self.last_char

    def read_buffer(self, n):
        res = []
        for _ in range(n):
            ch = self.read()
            if ch == END_OF_STREAM:
                break
            res.append(ch)
        return res

    def read_line(self):
        if self.look_ahead() == END_OF_STREAM:
            return None
        buffer = []
        while True:
            current = self.read()
            if current == ord(CR):
                next_ch = self.look_ahead()
                if next_ch == ord(LF):
                    self.read()
            if current in (END_OF_STREAM, ord(LF), ord(CR)):
                break
            buffer.append(chr(current))
        return "".join(buffer)


def _is_trim_char(ch):
    return ord(ch) <= ord(SP)


def _trim(s):
    count = len(s)
    length = count
    pos = 0
    while pos < length and _is_trim_char(s[pos]):
        pos += 1
    while pos < length and _is_trim_char(s[length - 1]):
        length -= 1
    return s[pos:length]


def _validate_bool(name, value):
    if not isinstance(value, bool):
        raise IllegalArgumentException(f"{name} must be a boolean, got {type(value).__name__}")
    return value


def _validate_char_or_none(name, value, allow_none=True):
    if value is None:
        if not allow_none:
            raise IllegalArgumentException(f"{name} cannot be null")
        return None
    if not isinstance(value, str) or len(value) != 1:
        raise IllegalArgumentException(f"{name} must be one character string, got {value!r}")
    return value


class CSVFormatResolved:
    def __init__(self, config=None):
        cfg = config or {}

        if "delimiter" in cfg:
            delim = cfg["delimiter"]
            if not isinstance(delim, str) or len(delim) != 1:
                raise IllegalArgumentException(f"The delimiter must be one character, got {delim!r}")
            self.delimiter = delim
        else:
            self.delimiter = ","

        if "quote" in cfg:
            self.quote_character = _validate_char_or_none("quote", cfg["quote"], allow_none=True)
        else:
            self.quote_character = '"'

        if "escape" in cfg:
            self.escape_character = _validate_char_or_none("escape", cfg["escape"], allow_none=True)
        else:
            self.escape_character = None

        if "comment_marker" in cfg:
            self.comment_marker = _validate_char_or_none("comment_marker", cfg["comment_marker"], allow_none=True)
        else:
            self.comment_marker = None

        if "record_separator" in cfg:
            rec_sep = cfg["record_separator"]
            if rec_sep is not None and not isinstance(rec_sep, str):
                raise IllegalArgumentException("record_separator must be a string or null")
            self.record_separator = rec_sep
        else:
            self.record_separator = CRLF

        if "null_string" in cfg:
            ns = cfg["null_string"]
            if ns is not None and not isinstance(ns, str):
                raise IllegalArgumentException("null_string must be a string or null")
            self.null_string = ns
        else:
            self.null_string = None

        if "quote_mode" in cfg:
            qm = cfg["quote_mode"]
            if qm is not None and qm not in VALID_QUOTE_MODES:
                raise IllegalArgumentException(f"Invalid quote_mode: {qm!r}")
            self.quote_mode = qm
        else:
            self.quote_mode = None

        if "ignore_empty_lines" in cfg:
            self.ignore_empty_lines = _validate_bool("ignore_empty_lines", cfg["ignore_empty_lines"])
        else:
            self.ignore_empty_lines = True

        if "ignore_surrounding_spaces" in cfg:
            self.ignore_surrounding_spaces = _validate_bool("ignore_surrounding_spaces", cfg["ignore_surrounding_spaces"])
        else:
            self.ignore_surrounding_spaces = False

        if "trim" in cfg:
            self.trim = _validate_bool("trim", cfg["trim"])
        else:
            self.trim = False

        if "trailing_delimiter" in cfg:
            self.trailing_delimiter = _validate_bool("trailing_delimiter", cfg["trailing_delimiter"])
        else:
            self.trailing_delimiter = False

        if self.quote_character is not None and self.null_string is not None:
            self.quoted_null_string = f"{self.quote_character}{self.null_string}{self.quote_character}"
        else:
            self.quoted_null_string = None

        self.validate()

    def validate(self):
        if not self.delimiter:
            raise IllegalArgumentException("The delimiter cannot be empty")
        if CR in self.delimiter or LF in self.delimiter:
            raise IllegalArgumentException("The delimiter cannot be a line break")
        if self.quote_character is not None and (self.quote_character in (CR, LF)):
            raise IllegalArgumentException("The quoteChar cannot be a line break")
        if self.escape_character is not None and (self.escape_character in (CR, LF)):
            raise IllegalArgumentException("The escape character cannot be a line break")
        if self.comment_marker is not None and (self.comment_marker in (CR, LF)):
            raise IllegalArgumentException("The comment start marker character cannot be a line break")

        if self.quote_character is not None and self.quote_character in self.delimiter:
            raise IllegalArgumentException(
                f"The quoteChar character and the delimiter cannot be the same ('{self.quote_character}')"
            )
        if self.escape_character is not None and self.escape_character in self.delimiter:
            raise IllegalArgumentException(
                f"The escape character and the delimiter cannot be the same ('{self.escape_character}')"
            )
        if self.comment_marker is not None and self.comment_marker in self.delimiter:
            raise IllegalArgumentException(
                f"The comment start character and the delimiter cannot be the same ('{self.comment_marker}')"
            )
        if self.quote_character is not None and self.quote_character == self.comment_marker:
            raise IllegalArgumentException(
                f"The comment start character and the quoteChar cannot be the same ('{self.comment_marker}')"
            )
        if self.escape_character is not None and self.escape_character == self.comment_marker:
            raise IllegalArgumentException(
                f"The comment start and the escape character cannot be the same ('{self.comment_marker}')"
            )
        if self.escape_character is None and self.quote_mode == "NONE":
            raise IllegalArgumentException("No quotes mode set but no escape character is set")

    def is_escape_character_set(self):
        return self.escape_character is not None

    def is_quote_character_set(self):
        return self.quote_character is not None

    def trim_value(self, value):
        return _trim(value) if self.trim else value

    def is_strict_quote_mode(self):
        return self.quote_mode in ("ALL_NON_NULL", "NON_NUMERIC")


class Lexer:
    def __init__(self, fmt, reader):
        self.format = fmt
        self.reader = reader
        self.delimiter = [ord(c) for c in fmt.delimiter]
        self.escape = ord(fmt.escape_character) if fmt.escape_character is not None else ord(DISABLED)
        self.quote_char = ord(fmt.quote_character) if fmt.quote_character is not None else ord(DISABLED)
        self.comment_start = ord(fmt.comment_marker) if fmt.comment_marker is not None else ord(DISABLED)
        self.ignore_surrounding_spaces = fmt.ignore_surrounding_spaces
        self.ignore_empty_lines = fmt.ignore_empty_lines
        self.delimiter_len = len(self.delimiter)
        self.is_last_token_delimiter = False
        self.first_eol = None

    def is_delimiter(self, ch):
        self.is_last_token_delimiter = False
        if ch != self.delimiter[0]:
            return False
        if self.delimiter_len == 1:
            self.is_last_token_delimiter = True
            return True
        needed = self.delimiter_len - 1
        buf = self.reader.look_ahead_n(needed)
        if len(buf) < needed:
            return False
        for i in range(needed):
            if buf[i] != self.delimiter[i + 1]:
                return False
        read_chars = self.reader.read_buffer(needed)
        self.is_last_token_delimiter = (len(read_chars) == needed)
        return self.is_last_token_delimiter

    def is_escape_delimiter(self):
        needed = 2 * self.delimiter_len - 1
        buf = self.reader.look_ahead_n(needed)
        if len(buf) < needed:
            return False
        if buf[0] != self.delimiter[0]:
            return False
        for i in range(1, self.delimiter_len):
            if buf[2 * i] != self.delimiter[i] or buf[2 * i - 1] != self.escape:
                return False
        read_chars = self.reader.read_buffer(needed)
        return len(read_chars) == needed

    def is_meta_char(self, ch):
        return ch in (self.escape, self.quote_char, self.comment_start)

    def is_start_of_line(self, ch):
        return ch in (ord(LF), ord(CR), UNDEFINED)

    def is_end_of_file(self, ch):
        return ch == END_OF_STREAM

    def read_end_of_line(self, ch):
        if ch == ord(CR) and self.reader.look_ahead() == ord(LF):
            ch = self.reader.read()
            if self.first_eol is None:
                self.first_eol = CRLF
        if self.first_eol is None:
            if ch == ord(LF):
                self.first_eol = LF
            elif ch == ord(CR):
                self.first_eol = CR
        return ch in (ord(LF), ord(CR))

    def read_escape(self):
        ch = self.reader.read()
        if ch == ord("r"):
            return ord(CR)
        if ch == ord("n"):
            return ord(LF)
        if ch == ord("t"):
            return ord(TAB)
        if ch == ord("b"):
            return ord(BACKSPACE)
        if ch == ord("f"):
            return ord(FF)
        if ch in (ord(CR), ord(LF), ord(FF), ord(TAB), ord(BACKSPACE)):
            return ch
        if ch == END_OF_STREAM:
            raise CSVParseError("EOF whilst processing escape sequence")
        if self.is_meta_char(ch):
            return ch
        return END_OF_STREAM

    def trim_trailing_spaces(self, content_list):
        while content_list and chr(content_list[-1]).isspace():
            content_list.pop()

    def next_token(self, token):
        last_char = self.reader.get_last_char()
        c = self.reader.read()
        eol = self.read_end_of_line(c)

        if self.ignore_empty_lines:
            while eol and self.is_start_of_line(last_char):
                last_char = c
                c = self.reader.read()
                eol = self.read_end_of_line(c)
                if self.is_end_of_file(c):
                    token.type = Token.EOF
                    return token

        if self.is_end_of_file(last_char) or (not self.is_last_token_delimiter and self.is_end_of_file(c)):
            token.type = Token.EOF
            return token

        if self.is_start_of_line(last_char) and c == self.comment_start:
            line = self.reader.read_line()
            if line is None:
                token.type = Token.EOF
                return token
            comment_str = line.strip()
            token.content.extend(ord(x) for x in comment_str)
            token.type = Token.COMMENT
            return token

        while token.type == Token.INVALID:
            if self.ignore_surrounding_spaces:
                while c != END_OF_STREAM and chr(c).isspace() and not self.is_delimiter(c) and not eol:
                    c = self.reader.read()
                    eol = self.read_end_of_line(c)

            if self.is_delimiter(c):
                token.type = Token.TOKEN
            elif eol:
                token.type = Token.EORECORD
            elif c == self.quote_char:
                self.parse_encapsulated_token(token)
            elif self.is_end_of_file(c):
                token.type = Token.EOF
                token.is_ready = True
            else:
                self.parse_simple_token(token, c)
        return token

    def parse_encapsulated_token(self, token):
        token.is_quoted = True
        start_line_number = self.reader.get_current_line_number()
        while True:
            c = self.reader.read()
            if c == self.escape:
                if self.is_escape_delimiter():
                    token.content.extend(self.delimiter)
                else:
                    unescaped = self.read_escape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(c)
                        token.content.append(self.reader.get_last_char())
                    else:
                        token.content.append(unescaped)
            elif c == self.quote_char:
                if self.reader.look_ahead() == self.quote_char:
                    c = self.reader.read()
                    token.content.append(c)
                else:
                    while True:
                        c = self.reader.read()
                        if self.is_delimiter(c):
                            token.type = Token.TOKEN
                            return token
                        if self.is_end_of_file(c):
                            token.type = Token.EOF
                            token.is_ready = True
                            return token
                        if self.read_end_of_line(c):
                            token.type = Token.EORECORD
                            return token
                        if not chr(c).isspace():
                            raise CSVParseError(
                                f"(line {self.reader.get_current_line_number()}) invalid char between encapsulated token and delimiter"
                            )
            elif self.is_end_of_file(c):
                raise CSVParseError(
                    f"(startline {start_line_number}) EOF reached before encapsulated token finished"
                )
            else:
                token.content.append(c)

    def parse_simple_token(self, token, ch):
        while True:
            if self.read_end_of_line(ch):
                token.type = Token.EORECORD
                break
            if self.is_end_of_file(ch):
                token.type = Token.EOF
                token.is_ready = True
                break
            if self.is_delimiter(ch):
                token.type = Token.TOKEN
                break
            if ch == self.escape:
                if self.is_escape_delimiter():
                    token.content.extend(self.delimiter)
                else:
                    unescaped = self.read_escape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(ch)
                        token.content.append(self.reader.get_last_char())
                    else:
                        token.content.append(unescaped)
            else:
                token.content.append(ch)
            ch = self.reader.read()

        if self.ignore_surrounding_spaces:
            self.trim_trailing_spaces(token.content)
        return token


def _handle_null(fmt, input_str, is_quoted):
    null_string = fmt.null_string
    strict_quote_mode = fmt.is_strict_quote_mode()
    if input_str == null_string:
        return input_str if (strict_quote_mode and is_quoted) else None
    if strict_quote_mode and null_string is None and input_str == "" and not is_quoted:
        return None
    return input_str


def parse_csv(text, config=None):
    fmt = CSVFormatResolved(config)
    reader = ExtendedBufferedReader(text)
    lexer = Lexer(fmt, reader)
    reusable_token = Token()
    records = []
    record_list = []

    def add_record_value(last_record):
        raw_str = "".join(chr(x) for x in reusable_token.content)
        input_val = fmt.trim_value(raw_str)
        if last_record and input_val == "" and fmt.trailing_delimiter:
            return
        record_list.append(_handle_null(fmt, input_val, reusable_token.is_quoted))

    while True:
        record_list.clear()
        while True:
            reusable_token.reset()
            lexer.next_token(reusable_token)
            if reusable_token.type == Token.TOKEN:
                add_record_value(False)
            elif reusable_token.type == Token.EORECORD:
                add_record_value(True)
            elif reusable_token.type == Token.EOF:
                if reusable_token.is_ready:
                    add_record_value(True)
                break
            elif reusable_token.type == Token.INVALID:
                raise CSVParseError(f"(line {lexer.reader.get_current_line_number()}) invalid parse sequence")
            elif reusable_token.type == Token.COMMENT:
                reusable_token.type = Token.TOKEN
            else:
                raise CSVParseError(f"Unexpected Token type: {reusable_token.type}")

            if reusable_token.type != Token.TOKEN:
                break

        if record_list:
            records.append(list(record_list))
        elif reusable_token.type == Token.EOF:
            break

        if reusable_token.type == Token.EOF:
            break

    return records


def _is_delimiter_match(char_seq, pos, delim):
    delim_len = len(delim)
    if char_seq[pos] != delim[0]:
        return False
    if pos + delim_len > len(char_seq):
        return False
    return char_seq[pos:pos + delim_len] == delim


def _print_with_escapes(fmt, char_seq, out):
    start = 0
    pos = 0
    length = len(char_seq)
    delim = fmt.delimiter
    delim_len = len(delim)
    escape = fmt.escape_character

    while pos < length:
        c = char_seq[pos]
        is_delim_start = _is_delimiter_match(char_seq, pos, delim)
        if c == CR or c == LF or c == escape or is_delim_start:
            if pos > start:
                out.write(char_seq[start:pos])
            if c == LF:
                c = "n"
            elif c == CR:
                c = "r"
            out.write(escape)
            out.write(c)
            if is_delim_start:
                for _ in range(1, delim_len):
                    pos += 1
                    c = char_seq[pos]
                    out.write(escape)
                    out.write(c)
            start = pos + 1
        pos += 1
    if pos > start:
        out.write(char_seq[start:pos])


def _print_with_quotes(fmt, obj, char_seq, out, new_record):
    quote = False
    pos = 0
    length = len(char_seq)
    delim = fmt.delimiter
    quote_char = fmt.quote_character
    escape_char = fmt.escape_character if fmt.is_escape_character_set() else quote_char

    quote_mode = fmt.quote_mode if fmt.quote_mode is not None else "MINIMAL"

    if quote_mode in ("ALL", "ALL_NON_NULL"):
        quote = True
    elif quote_mode == "NON_NUMERIC":
        quote = not isinstance(obj, numbers.Number)
    elif quote_mode == "NONE":
        _print_with_escapes(fmt, char_seq, out)
        return
    elif quote_mode == "MINIMAL":
        if length <= 0:
            if new_record:
                quote = True
        else:
            c = char_seq[pos]
            if ord(c) <= ord(COMMENT):
                quote = True
            else:
                while pos < length:
                    c = char_seq[pos]
                    if (c == LF or c == CR or c == quote_char or c == escape_char or
                            _is_delimiter_match(char_seq, pos, delim)):
                        quote = True
                        break
                    pos += 1
                if not quote:
                    pos = length - 1
                    c = char_seq[pos]
                    if _is_trim_char(c):
                        quote = True
        if not quote:
            out.write(char_seq)
            return
    else:
        raise IllegalArgumentException(f"Unexpected Quote value: {quote_mode}")

    if not quote:
        out.write(char_seq)
        return

    out.write(quote_char)
    pos_idx = pos
    start_idx = 0
    while pos_idx < length:
        c = char_seq[pos_idx]
        if c == quote_char or c == escape_char:
            out.write(char_seq[start_idx:pos_idx])
            out.write(escape_char)
            start_idx = pos_idx
        pos_idx += 1
    out.write(char_seq[start_idx:pos_idx])
    out.write(quote_char)


def _print_field(fmt, value, out, new_record):
    if value is None:
        if fmt.null_string is None:
            char_seq = ""
        elif fmt.quote_mode == "ALL":
            char_seq = fmt.quoted_null_string
        else:
            char_seq = fmt.null_string
    else:
        char_seq = str(value)

    char_seq = fmt.trim_value(char_seq)

    if not new_record:
        out.write(fmt.delimiter)

    if value is None:
        out.write(char_seq)
    elif fmt.is_quote_character_set():
        _print_with_quotes(fmt, value, char_seq, out, new_record)
    elif fmt.is_escape_character_set():
        _print_with_escapes(fmt, char_seq, out)
    else:
        out.write(char_seq)


def print_csv(records, config=None):
    fmt = CSVFormatResolved(config)
    out = io.StringIO()

    for record in records:
        first = True
        for val in record:
            _print_field(fmt, val, out, first)
            first = False
        if fmt.trailing_delimiter:
            out.write(fmt.delimiter)
        if fmt.record_separator is not None:
            out.write(fmt.record_separator)

    return out.getvalue()
