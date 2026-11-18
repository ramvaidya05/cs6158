import io
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class CSVParseError(Exception):
    pass


class IllegalArgumentException(Exception):
    pass


class QuoteMode(Enum):
    ALL = "ALL"
    ALL_NON_NULL = "ALL_NON_NULL"
    MINIMAL = "MINIMAL"
    NON_NUMERIC = "NON_NUMERIC"
    NONE = "NONE"


class _CSVFormat:
    def __init__(
        self,
        delimiter: str = ",",
        quote: Optional[str] = '"',
        quote_mode: Optional[QuoteMode] = None,
        comment_marker: Optional[str] = None,
        escape: Optional[str] = None,
        ignore_surrounding_spaces: bool = False,
        ignore_empty_lines: bool = True,
        record_separator: Optional[str] = "\r\n",
        null_string: Optional[str] = None,
        trim: bool = False,
        trailing_delimiter: bool = False,
    ):
        self.delimiter = delimiter
        self.quote = quote
        self.quote_mode = quote_mode
        self.comment_marker = comment_marker
        self.escape = escape
        self.ignore_surrounding_spaces = ignore_surrounding_spaces
        self.ignore_empty_lines = ignore_empty_lines
        self.record_separator = record_separator
        self.null_string = null_string
        self.trim = trim
        self.trailing_delimiter = trailing_delimiter
        self.validate()

    def validate(self):
        if "\r" in self.delimiter or "\n" in self.delimiter:
            raise IllegalArgumentException("The delimiter cannot be a line break")
        if not self.delimiter:
            raise IllegalArgumentException("The delimiter cannot be empty")
        if self.quote is not None and self.quote in self.delimiter:
            raise IllegalArgumentException("The quoteChar character and the delimiter cannot be the same")
        if self.escape is not None and self.escape in self.delimiter:
            raise IllegalArgumentException("The escape character and the delimiter cannot be the same")
        if self.comment_marker is not None and self.comment_marker in self.delimiter:
            raise IllegalArgumentException("The comment start character and the delimiter cannot be the same")
        if self.quote is not None and self.comment_marker is not None and self.quote == self.comment_marker:
            raise IllegalArgumentException("The comment start character and the quoteChar cannot be the same")
        if self.escape is not None and self.comment_marker is not None and self.escape == self.comment_marker:
            raise IllegalArgumentException("The comment start and the escape character cannot be the same")
        if self.escape is None and self.quote_mode == QuoteMode.NONE:
            raise IllegalArgumentException("No quotes mode set but no escape character is set")


def _check_bool(config: Dict[str, Any], key: str, default: bool) -> bool:
    if key not in config:
        return default
    val = config[key]
    if not isinstance(val, bool):
        raise IllegalArgumentException(f"{key} must be a boolean")
    return val


def _build_format(config: Optional[Dict[str, Any]]) -> _CSVFormat:
    if config is None:
        config = {}
    delimiter = config.get("delimiter", ",")
    if delimiter is None:
        raise IllegalArgumentException("delimiter cannot be null")
    if not isinstance(delimiter, str) or len(delimiter) != 1:
        raise IllegalArgumentException("delimiter must be one UTF-16 character")

    quote = config.get("quote", '"')
    if quote is not None and (not isinstance(quote, str) or len(quote) != 1):
        raise IllegalArgumentException("quote must be one UTF-16 character or null")

    escape = config.get("escape", None)
    if escape is not None and (not isinstance(escape, str) or len(escape) != 1):
        raise IllegalArgumentException("escape must be one UTF-16 character or null")

    record_separator = config.get("record_separator", "\r\n")
    if record_separator is not None and not isinstance(record_separator, str):
        raise IllegalArgumentException("record_separator must be a string or null")

    null_string = config.get("null_string", None)
    if null_string is not None and not isinstance(null_string, str):
        raise IllegalArgumentException("null_string must be a string or null")

    raw_quote_mode = config.get("quote_mode", None)
    quote_mode: Optional[QuoteMode] = None
    if raw_quote_mode is not None:
        if isinstance(raw_quote_mode, QuoteMode):
            quote_mode = raw_quote_mode
        elif isinstance(raw_quote_mode, str):
            try:
                quote_mode = QuoteMode[raw_quote_mode]
            except KeyError:
                raise IllegalArgumentException(f"Unknown quote_mode: {raw_quote_mode}")
        else:
            raise IllegalArgumentException("quote_mode must be string or QuoteMode")

    ignore_empty_lines = _check_bool(config, "ignore_empty_lines", True)
    ignore_surrounding_spaces = _check_bool(config, "ignore_surrounding_spaces", False)
    trim = _check_bool(config, "trim", False)
    trailing_delimiter = _check_bool(config, "trailing_delimiter", False)

    return _CSVFormat(
        delimiter=delimiter,
        quote=quote,
        quote_mode=quote_mode,
        escape=escape,
        ignore_surrounding_spaces=ignore_surrounding_spaces,
        ignore_empty_lines=ignore_empty_lines,
        record_separator=record_separator,
        null_string=null_string,
        trim=trim,
        trailing_delimiter=trailing_delimiter,
    )


class _ExtendedReader:
    UNDEFINED = -2
    END_OF_STREAM = -1

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.len = len(text)
        self.last_char = self.UNDEFINED
        self.eol_counter = 0
        self.character_position = 0

    def read(self) -> int:
        if self.pos >= self.len:
            current = self.END_OF_STREAM
        else:
            current = ord(self.text[self.pos])
            self.pos += 1

        if (
            current == 13
            or (current == 10 and self.last_char != 13)
            or (current == self.END_OF_STREAM and self.last_char not in (13, 10, self.END_OF_STREAM))
        ):
            self.eol_counter += 1

        self.last_char = current
        if current != self.END_OF_STREAM:
            self.character_position += 1
        return current

    def look_ahead(self, n: int = 1) -> Union[int, List[int]]:
        if n == 1:
            if self.pos >= self.len:
                return self.END_OF_STREAM
            return ord(self.text[self.pos])
        res = []
        for i in range(n):
            p = self.pos + i
            if p < self.len:
                res.append(ord(self.text[p]))
            else:
                break
        return res

    def read_line(self) -> Optional[str]:
        if self.look_ahead() == self.END_OF_STREAM:
            return None
        buf = []
        while True:
            c = self.read()
            if c == 13:
                if self.look_ahead() == 10:
                    self.read()
            if c in (self.END_OF_STREAM, 10, 13):
                break
            buf.append(chr(c))
        return "".join(buf)

    def get_current_line_number(self) -> int:
        if self.last_char in (13, 10, self.UNDEFINED, self.END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1


class _TokenType(Enum):
    INVALID = 0
    TOKEN = 1
    EOF = 2
    EORECORD = 3
    COMMENT = 4


class _Token:
    def __init__(self):
        self.type = _TokenType.INVALID
        self.content = []
        self.is_ready = False
        self.is_quoted = False

    def reset(self):
        self.type = _TokenType.INVALID
        self.content.clear()
        self.is_ready = False
        self.is_quoted = False

    def get_content(self) -> str:
        return "".join(self.content)


class _Lexer:
    DISABLED = 0xFFFE

    def __init__(self, fmt: _CSVFormat, reader: _ExtendedReader):
        self.format = fmt
        self.reader = reader
        self.delimiter = [ord(c) for c in fmt.delimiter]
        self.escape = ord(fmt.escape) if fmt.escape is not None else self.DISABLED
        self.quote_char = ord(fmt.quote) if fmt.quote is not None else self.DISABLED
        self.comment_start = ord(fmt.comment_marker) if fmt.comment_marker is not None else self.DISABLED
        self.ignore_surrounding_spaces = fmt.ignore_surrounding_spaces
        self.ignore_empty_lines = fmt.ignore_empty_lines
        self.is_last_token_delimiter = False

    def is_delimiter(self, ch: int) -> bool:
        self.is_last_token_delimiter = False
        if ch != self.delimiter[0]:
            return False
        if len(self.delimiter) == 1:
            self.is_last_token_delimiter = True
            return True
        ahead = self.reader.look_ahead(len(self.delimiter) - 1)
        if not isinstance(ahead, list) or len(ahead) < len(self.delimiter) - 1:
            return False
        for i in range(len(ahead)):
            if ahead[i] != self.delimiter[i + 1]:
                return False
        for _ in range(len(ahead)):
            self.reader.read()
        self.is_last_token_delimiter = True
        return True

    def is_escape_delimiter(self) -> bool:
        needed_len = 2 * len(self.delimiter) - 1
        ahead = self.reader.look_ahead(needed_len)
        if not isinstance(ahead, list) or len(ahead) < needed_len:
            return False
        if ahead[0] != self.delimiter[0]:
            return False
        for i in range(1, len(self.delimiter)):
            if ahead[2 * i] != self.delimiter[i] or ahead[2 * i - 1] != self.escape:
                return False
        for _ in range(needed_len):
            self.reader.read()
        return True

    def is_start_of_line(self, ch: int) -> bool:
        return ch in (10, 13, _ExtendedReader.UNDEFINED)

    def is_end_of_file(self, ch: int) -> bool:
        return ch == _ExtendedReader.END_OF_STREAM

    def is_escape(self, ch: int) -> bool:
        return ch == self.escape

    def is_quote_char(self, ch: int) -> bool:
        return ch == self.quote_char

    def is_comment_start(self, ch: int) -> bool:
        return ch == self.comment_start

    def is_meta_char(self, ch: int) -> bool:
        return ch in (self.escape, self.quote_char, self.comment_start)

    def read_end_of_line(self, ch: int) -> bool:
        if ch == 13 and self.reader.look_ahead(1) == 10:
            self.reader.read()
            return True
        return ch in (10, 13)

    def read_escape(self) -> int:
        ch = self.reader.read()
        if ch == ord('r'):
            return 13
        elif ch == ord('n'):
            return 10
        elif ch == ord('t'):
            return 9
        elif ch == ord('b'):
            return 8
        elif ch == ord('f'):
            return 12
        elif ch in (13, 10, 12, 9, 8):
            return ch
        elif ch == _ExtendedReader.END_OF_STREAM:
            raise CSVParseError("EOF whilst processing escape sequence")
        else:
            if self.is_meta_char(ch):
                return ch
            return _ExtendedReader.END_OF_STREAM

    def trim_trailing_spaces(self, buf: List[str]):
        while buf and chr(ord(buf[-1])).isspace():
            buf.pop()

    def next_token(self, token: _Token) -> _Token:
        last_char = self.reader.last_char
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
            token.content.extend(list(comment))
            token.type = _TokenType.COMMENT
            return token

        while token.type == _TokenType.INVALID:
            if self.ignore_surrounding_spaces:
                while c != _ExtendedReader.END_OF_STREAM and chr(c).isspace() and not self.is_delimiter(c) and not eol:
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

    def parse_encapsulated_token(self, token: _Token) -> _Token:
        token.is_quoted = True
        start_line_number = self.reader.get_current_line_number()
        while True:
            c = self.reader.read()
            if self.is_escape(c):
                if self.is_escape_delimiter():
                    token.content.extend(self.format.delimiter)
                else:
                    unescaped = self.read_escape()
                    if unescaped == _ExtendedReader.END_OF_STREAM:
                        token.content.append(chr(c))
                        token.content.append(chr(self.reader.last_char))
                    else:
                        token.content.append(chr(unescaped))
            elif self.is_quote_char(c):
                if self.is_quote_char(self.reader.look_ahead(1)):
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
                        if not chr(c).isspace():
                            raise CSVParseError(
                                f"(line {self.reader.get_current_line_number()}) invalid char between encapsulated token and delimiter"
                            )
            elif self.is_end_of_file(c):
                raise CSVParseError(f"(startline {start_line_number}) EOF reached before encapsulated token finished")
            else:
                token.content.append(chr(c))

    def parse_simple_token(self, token: _Token, ch: int) -> _Token:
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
                    token.content.extend(self.format.delimiter)
                else:
                    unescaped = self.read_escape()
                    if unescaped == _ExtendedReader.END_OF_STREAM:
                        token.content.append(chr(ch))
                        token.content.append(chr(self.reader.last_char))
                    else:
                        token.content.append(chr(unescaped))
            else:
                token.content.append(chr(ch))
            ch = self.reader.read()

        if self.ignore_surrounding_spaces:
            self.trim_trailing_spaces(token.content)

        return token


def parse_csv(text: str, config: Optional[Dict[str, Any]] = None) -> List[List[Optional[str]]]:
    fmt = _build_format(config)
    reader = _ExtendedReader(text)
    lexer = _Lexer(fmt, reader)
    token = _Token()

    def is_strict_quote_mode():
        return fmt.quote_mode in (QuoteMode.ALL_NON_NULL, QuoteMode.NON_NUMERIC)

    def handle_null(inp: str, is_quoted: bool) -> Optional[str]:
        null_string = fmt.null_string
        strict = is_strict_quote_mode()
        if inp == null_string:
            return inp if strict and is_quoted else None
        if strict and null_string is None and inp == "" and not is_quoted:
            return None
        return inp

    records: List[List[Optional[str]]] = []
    record_list: List[Optional[str]] = []

    def add_record_value(last_record: bool):
        raw = token.get_content()
        val = raw.strip() if fmt.trim else raw
        if last_record and val == "" and fmt.trailing_delimiter:
            return
        record_list.append(handle_null(val, token.is_quoted))

    while True:
        record_list.clear()
        token.reset()
        while True:
            token.reset()
            lexer.next_token(token)
            if token.type == _TokenType.TOKEN:
                add_record_value(False)
            elif token.type == _TokenType.EORECORD:
                add_record_value(True)
                break
            elif token.type == _TokenType.EOF:
                if token.is_ready:
                    add_record_value(True)
                break
            elif token.type == _TokenType.COMMENT:
                token.type = _TokenType.TOKEN
            elif token.type == _TokenType.INVALID:
                raise CSVParseError(f"(line {reader.get_current_line_number()}) invalid parse sequence")

        if record_list:
            records.append(list(record_list))

        if token.type == _TokenType.EOF:
            break

    return records


def _is_trim_char(ch: str) -> bool:
    return ord(ch) <= ord(' ')


def _print_with_escapes(val: str, out: io.StringIO, fmt: _CSVFormat):
    start = 0
    pos = 0
    end = len(val)
    delim = fmt.delimiter
    delim_len = len(delim)
    escape = fmt.escape
    if escape is None:
        raise IllegalArgumentException("No escape character set")

    while pos < end:
        c = val[pos]
        is_delim_start = val[pos : pos + delim_len] == delim
        if c == "\r" or c == "\n" or c == escape or is_delim_start:
            if pos > start:
                out.write(val[start:pos])
            if c == "\n":
                c = "n"
            elif c == "\r":
                c = "r"
            out.write(escape)
            out.write(c)
            if is_delim_start:
                for _ in range(1, delim_len):
                    pos += 1
                    c = val[pos]
                    out.write(escape)
                    out.write(c)
            start = pos + 1
        pos += 1
    if pos > start:
        out.write(val[start:pos])


def _print_with_quotes(val: str, out: io.StringIO, new_record: bool, is_null: bool, fmt: _CSVFormat):
    quote = False
    start = 0
    pos = 0
    length = len(val)
    delim = fmt.delimiter
    delim_len = len(delim)
    quote_char = fmt.quote
    if quote_char is None:
        raise IllegalArgumentException("No quote character set")
    escape_char = fmt.escape if fmt.escape is not None else quote_char
    quote_mode = fmt.quote_mode if fmt.quote_mode is not None else QuoteMode.MINIMAL

    if quote_mode == QuoteMode.ALL:
        quote = True
    elif quote_mode == QuoteMode.ALL_NON_NULL:
        quote = not is_null
    elif quote_mode == QuoteMode.NON_NUMERIC:
        quote = True
    elif quote_mode == QuoteMode.NONE:
        _print_with_escapes(val, out, fmt)
        return
    elif quote_mode == QuoteMode.MINIMAL:
        if length <= 0:
            if new_record:
                quote = True
        else:
            c = val[0]
            if ord(c) <= ord('#'):
                quote = True
            else:
                while pos < length:
                    c = val[pos]
                    if (
                        c == "\n"
                        or c == "\r"
                        or c == quote_char
                        or c == escape_char
                        or val[pos : pos + delim_len] == delim
                    ):
                        quote = True
                        break
                    pos += 1
                if not quote:
                    c = val[length - 1]
                    if _is_trim_char(c):
                        quote = True
        if not quote:
            out.write(val)
            return
    else:
        raise IllegalArgumentException(f"Unexpected Quote value: {quote_mode}")

    if not quote:
        out.write(val)
        return

    out.write(quote_char)
    while pos < length:
        c = val[pos]
        if c == quote_char or c == escape_char:
            out.write(val[start:pos])
            out.write(escape_char)
            start = pos
        pos += 1
    out.write(val[start:pos])
    out.write(quote_char)


def _print_value(value: Optional[str], out: io.StringIO, new_record: bool, fmt: _CSVFormat):
    is_null = value is None
    if is_null:
        if fmt.null_string is None:
            char_sequence = ""
        elif fmt.quote_mode == QuoteMode.ALL:
            char_sequence = (fmt.quote or "") + fmt.null_string + (fmt.quote or "")
        else:
            char_sequence = fmt.null_string
    else:
        char_sequence = str(value)

    if fmt.trim:
        char_sequence = char_sequence.strip()

    if not new_record:
        out.write(fmt.delimiter)

    if is_null:
        out.write(char_sequence)
    elif fmt.quote is not None:
        _print_with_quotes(char_sequence, out, new_record, is_null, fmt)
    elif fmt.escape is not None:
        _print_with_escapes(char_sequence, out, fmt)
    else:
        out.write(char_sequence)


def print_csv(records: List[List[Optional[str]]], config: Optional[Dict[str, Any]] = None) -> str:
    fmt = _build_format(config)
    out = io.StringIO()

    for record in records:
        for i, val in enumerate(record):
            _print_value(val, out, i == 0, fmt)
        if fmt.trailing_delimiter:
            out.write(fmt.delimiter)
        if fmt.record_separator is not None:
            out.write(fmt.record_separator)

    return out.getvalue()
