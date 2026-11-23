import unicodedata
from enum import Enum
from typing import Any, List, Optional


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


END_OF_STREAM = -1
UNDEFINED = -2
DISABLED = 0xFFFE

CR = "\r"
LF = "\n"
CRLF = "\r\n"
SP = " "
BACKSLASH = "\\"
BACKSPACE = "\b"
FF = "\f"
TAB = "\t"


def _is_java_whitespace(code_point: int) -> bool:
    if code_point in (0x0009, 0x000A, 0x000B, 0x000C, 0x000D, 0x001C, 0x001D, 0x001E, 0x001F):
        return True
    cat = unicodedata.category(chr(code_point))
    if cat in ('Zs', 'Zl', 'Zp'):
        if code_point in (0x00A0, 0x2007, 0x202F):
            return False
        return True
    return False


def _java_trim(s: str) -> str:
    start = 0
    end = len(s)
    while start < end and ord(s[start]) <= 0x0020:
        start += 1
    while end > start and ord(s[end - 1]) <= 0x0020:
        end -= 1
    return s[start:end]


def _validate_char_param(name: str, val: Any, allow_none: bool = False) -> Optional[int]:
    if val is None:
        if allow_none:
            return None
        raise IllegalArgumentException(f"{name} cannot be null")
    if not isinstance(val, str):
        raise IllegalArgumentException(f"{name} must be a string character")
    encoded = val.encode('utf-16-le')
    if len(encoded) != 2:
        raise IllegalArgumentException(f"{name} must be exactly one UTF-16 code unit")
    code_unit = ord(val)
    return code_unit


def _validate_bool_param(name: str, val: Any, default: bool) -> bool:
    if val is None:
        return default
    if not isinstance(val, bool):
        raise IllegalArgumentException(f"{name} must be a boolean")
    return val


class CSVFormatConfig:
    def __init__(self, config: Optional[dict] = None):
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise IllegalArgumentException("config must be a dictionary")

        delim_raw = config.get("delimiter", ",")
        delim_cu = _validate_char_param("delimiter", delim_raw, allow_none=False)
        if delim_cu is None or chr(delim_cu) in (CR, LF):
            raise IllegalArgumentException("The delimiter cannot be a line break or empty")
        self.delimiter = chr(delim_cu)

        quote_raw = config.get("quote", '"') if "quote" in config else '"'
        quote_cu = _validate_char_param("quote", quote_raw, allow_none=True)
        if quote_cu is not None and chr(quote_cu) in (CR, LF):
            raise IllegalArgumentException("The quoteChar cannot be a line break")
        self.quote_char = chr(quote_cu) if quote_cu is not None else None

        escape_raw = config.get("escape", None)
        escape_cu = _validate_char_param("escape", escape_raw, allow_none=True)
        if escape_cu is not None and chr(escape_cu) in (CR, LF):
            raise IllegalArgumentException("The escape character cannot be a line break")
        self.escape_char = chr(escape_cu) if escape_cu is not None else None

        rec_sep = config.get("record_separator", CRLF)
        if rec_sep is not None and not isinstance(rec_sep, str):
            raise IllegalArgumentException("record_separator must be a string or None")
        self.record_separator = rec_sep

        null_str = config.get("null_string", None)
        if null_str is not None and not isinstance(null_str, str):
            raise IllegalArgumentException("null_string must be a string or None")
        self.null_string = null_str

        qm_raw = config.get("quote_mode", None)
        if qm_raw is not None:
            if isinstance(qm_raw, QuoteMode):
                self.quote_mode = qm_raw
            elif isinstance(qm_raw, str):
                try:
                    self.quote_mode = QuoteMode[qm_raw]
                except KeyError:
                    raise IllegalArgumentException(f"Unknown quote_mode: {qm_raw}")
            else:
                raise IllegalArgumentException("Invalid quote_mode type")
        else:
            self.quote_mode = None

        self.ignore_empty_lines = _validate_bool_param("ignore_empty_lines", config.get("ignore_empty_lines"), True)
        self.ignore_surrounding_spaces = _validate_bool_param("ignore_surrounding_spaces", config.get("ignore_surrounding_spaces"), False)
        self.trim = _validate_bool_param("trim", config.get("trim"), False)
        self.trailing_delimiter = _validate_bool_param("trailing_delimiter", config.get("trailing_delimiter"), False)

        self._validate()

    def _validate(self):
        if CR in self.delimiter or LF in self.delimiter:
            raise IllegalArgumentException("The delimiter cannot be a line break")
        if self.quote_char is not None and self.quote_char in self.delimiter:
            raise IllegalArgumentException(f"The quoteChar character and the delimiter cannot be the same ('{self.quote_char}')")
        if self.escape_char is not None and self.escape_char in self.delimiter:
            raise IllegalArgumentException(f"The escape character and the delimiter cannot be the same ('{self.escape_char}')")
        if self.escape_char is None and self.quote_mode == QuoteMode.NONE:
            raise IllegalArgumentException("No quotes mode set but no escape character is set")


class ExtendedBufferedReader:
    def __init__(self, text: str):
        self.chars = [ord(c) for c in text]
        self.len = len(self.chars)
        self.pos = 0
        self.last_char = UNDEFINED
        self.eol_counter = 0

    def get_last_char(self) -> int:
        return self.last_char

    def get_current_line_number(self) -> int:
        if self.last_char in (ord(CR), ord(LF), UNDEFINED, END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1

    def look_ahead(self, n: int = 1) -> List[int]:
        res = []
        for i in range(n):
            p = self.pos + i
            if p < self.len:
                res.append(self.chars[p])
            else:
                res.append(END_OF_STREAM)
        return res

    def read(self) -> int:
        if self.pos >= self.len:
            current = END_OF_STREAM
        else:
            current = self.chars[self.pos]
            self.pos += 1

        if current == ord(CR) or (current == ord(LF) and self.last_char != ord(CR)) or \
           (current == END_OF_STREAM and self.last_char not in (ord(CR), ord(LF), END_OF_STREAM)):
            self.eol_counter += 1

        self.last_char = current
        return current

    def read_buffer(self, n: int) -> List[int]:
        res = []
        for _ in range(n):
            c = self.read()
            if c == END_OF_STREAM:
                break
            res.append(c)
        return res


class TokenType(Enum):
    INVALID = "INVALID"
    TOKEN = "TOKEN"
    EOF = "EOF"
    EORECORD = "EORECORD"
    COMMENT = "COMMENT"


class Token:
    def __init__(self):
        self.type = TokenType.INVALID
        self.content = []
        self.is_ready = False
        self.is_quoted = False

    def reset(self):
        self.type = TokenType.INVALID
        self.content.clear()
        self.is_ready = False
        self.is_quoted = False


class Lexer:
    def __init__(self, format_config: CSVFormatConfig, reader: ExtendedBufferedReader):
        self.reader = reader
        self.delimiter = [ord(c) for c in format_config.delimiter]
        self.escape = ord(format_config.escape_char) if format_config.escape_char is not None else DISABLED
        self.quote_char = ord(format_config.quote_char) if format_config.quote_char is not None else DISABLED
        self.comment_start = DISABLED
        self.ignore_surrounding_spaces = format_config.ignore_surrounding_spaces
        self.ignore_empty_lines = format_config.ignore_empty_lines
        self.is_last_token_delimiter = False

    def is_delimiter(self, ch: int) -> bool:
        self.is_last_token_delimiter = False
        if ch != self.delimiter[0]:
            return False
        if len(self.delimiter) == 1:
            self.is_last_token_delimiter = True
            return True
        lookahead = self.reader.look_ahead(len(self.delimiter) - 1)
        for i in range(len(lookahead)):
            if lookahead[i] != self.delimiter[i + 1]:
                return False
        self.reader.read_buffer(len(self.delimiter) - 1)
        self.is_last_token_delimiter = True
        return True

    def is_escape(self, ch: int) -> bool:
        return ch == self.escape

    def is_quote_char(self, ch: int) -> bool:
        return ch == self.quote_char

    def is_start_of_line(self, ch: int) -> bool:
        return ch in (ord(LF), ord(CR), UNDEFINED)

    def is_escape_delimiter(self) -> bool:
        needed = 2 * len(self.delimiter) - 1
        lookahead = self.reader.look_ahead(needed)
        if lookahead[0] != self.delimiter[0]:
            return False
        for i in range(1, len(self.delimiter)):
            if lookahead[2 * i] != self.delimiter[i] or lookahead[2 * i - 1] != self.escape:
                return False
        self.reader.read_buffer(needed)
        return True

    def is_meta_char(self, ch: int) -> bool:
        return ch in (self.escape, self.quote_char, self.comment_start)

    def read_end_of_line(self, ch: int) -> bool:
        if ch == ord(CR) and self.reader.look_ahead(1)[0] == ord(LF):
            ch = self.reader.read()
        return ch in (ord(LF), ord(CR))

    def read_escape(self) -> int:
        ch = self.reader.read()
        if ch == ord('r'):
            return ord(CR)
        elif ch == ord('n'):
            return ord(LF)
        elif ch == ord('t'):
            return ord(TAB)
        elif ch == ord('b'):
            return ord(BACKSPACE)
        elif ch == ord('f'):
            return ord(FF)
        elif ch in (ord(CR), ord(LF), ord(FF), ord(TAB), ord(BACKSPACE)):
            return ch
        elif ch == END_OF_STREAM:
            raise CSVParseError("EOF whilst processing escape sequence")
        else:
            if self.is_meta_char(ch) or (len(self.delimiter) > 0 and ch == self.delimiter[0]):
                return ch
            return END_OF_STREAM

    def trim_trailing_spaces(self, content: List[int]):
        while content and _is_java_whitespace(content[-1]):
            content.pop()

    def next_token(self, token: Token) -> Token:
        last_char = self.reader.get_last_char()
        c = self.reader.read()
        eol = self.read_end_of_line(c)

        if self.ignore_empty_lines:
            while eol and self.is_start_of_line(last_char):
                last_char = c
                c = self.reader.read()
                eol = self.read_end_of_line(c)
                if c == END_OF_STREAM:
                    token.type = TokenType.EOF
                    return token

        if last_char == END_OF_STREAM or (not self.is_last_token_delimiter and c == END_OF_STREAM):
            token.type = TokenType.EOF
            return token

        while token.type == TokenType.INVALID:
            if self.ignore_surrounding_spaces:
                while _is_java_whitespace(c) and not self.is_delimiter(c) and not eol:
                    c = self.reader.read()
                    eol = self.read_end_of_line(c)

            if self.is_delimiter(c):
                token.type = TokenType.TOKEN
            elif eol:
                token.type = TokenType.EORECORD
            elif self.is_quote_char(c):
                self.parse_encapsulated_token(token)
            elif c == END_OF_STREAM:
                token.type = TokenType.EOF
                token.is_ready = True
            else:
                self.parse_simple_token(token, c)

        return token

    def parse_encapsulated_token(self, token: Token) -> Token:
        token.is_quoted = True
        start_line_number = self.reader.get_current_line_number()
        while True:
            c = self.reader.read()
            if self.is_escape(c):
                if self.is_escape_delimiter():
                    token.content.extend(self.delimiter)
                else:
                    unescaped = self.read_escape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(c)
                        token.content.append(self.reader.get_last_char())
                    else:
                        token.content.append(unescaped)
            elif self.is_quote_char(c):
                if self.is_quote_char(self.reader.look_ahead(1)[0]):
                    c = self.reader.read()
                    token.content.append(c)
                else:
                    while True:
                        c = self.reader.read()
                        if self.is_delimiter(c):
                            token.type = TokenType.TOKEN
                            return token
                        if c == END_OF_STREAM:
                            token.type = TokenType.EOF
                            token.is_ready = True
                            return token
                        if self.read_end_of_line(c):
                            token.type = TokenType.EORECORD
                            return token
                        if not _is_java_whitespace(c):
                            raise CSVParseError(f"(line {self.reader.get_current_line_number()}) invalid char between encapsulated token and delimiter")
            elif c == END_OF_STREAM:
                raise CSVParseError(f"(startline {start_line_number}) EOF reached before encapsulated token finished")
            else:
                token.content.append(c)

    def parse_simple_token(self, token: Token, ch: int) -> Token:
        while True:
            if self.read_end_of_line(ch):
                token.type = TokenType.EORECORD
                break
            if ch == END_OF_STREAM:
                token.type = TokenType.EOF
                token.is_ready = True
                break
            if self.is_delimiter(ch):
                token.type = TokenType.TOKEN
                break
            if self.is_escape(ch):
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


def parse_csv(text: str, config: Optional[dict] = None) -> List[List[Optional[str]]]:
    if not isinstance(text, str):
        raise IllegalArgumentException("text must be a string")
    format_config = CSVFormatConfig(config)
    reader = ExtendedBufferedReader(text)
    lexer = Lexer(format_config, reader)
    reusable_token = Token()

    records = []
    record_list = []

    def is_strict_quote_mode() -> bool:
        return format_config.quote_mode in (QuoteMode.ALL_NON_NULL, QuoteMode.NON_NUMERIC)

    def handle_null(inp: str, is_quoted: bool) -> Optional[str]:
        null_string = format_config.null_string
        strict = is_strict_quote_mode()
        if inp == null_string:
            return inp if (strict and is_quoted) else None
        if strict and null_string is None and inp == "" and not is_quoted:
            return None
        return inp

    def add_record_value(last_record: bool):
        raw_str = "".join(chr(c) for c in reusable_token.content)
        inp = _java_trim(raw_str) if format_config.trim else raw_str
        if last_record and inp == "" and format_config.trailing_delimiter:
            return
        record_list.append(handle_null(inp, reusable_token.is_quoted))

    while True:
        record_list.clear()
        while True:
            reusable_token.reset()
            lexer.next_token(reusable_token)
            if reusable_token.type == TokenType.TOKEN:
                add_record_value(False)
            elif reusable_token.type == TokenType.EORECORD:
                add_record_value(True)
            elif reusable_token.type == TokenType.EOF:
                if reusable_token.is_ready:
                    add_record_value(True)
            elif reusable_token.type == TokenType.INVALID:
                raise CSVParseError(f"(line {reader.get_current_line_number()}) invalid parse sequence")
            else:
                raise CSVParseError(f"Unexpected Token type: {reusable_token.type}")

            if reusable_token.type != TokenType.TOKEN:
                break

        if record_list:
            records.append(list(record_list))
        elif reusable_token.type == TokenType.EOF:
            break

        if reusable_token.type == TokenType.EOF and not reusable_token.is_ready:
            break

    return records


def _is_delimiter_at(char_seq: str, pos: int, delim: str) -> bool:
    if pos + len(delim) > len(char_seq):
        return False
    return char_seq[pos:pos + len(delim)] == delim


def _print_with_escapes(char_seq: str, escape: str, delim: str) -> str:
    out = []
    start = 0
    pos = 0
    end = len(char_seq)
    delim_len = len(delim)
    while pos < end:
        c = char_seq[pos]
        is_del_start = _is_delimiter_at(char_seq, pos, delim)
        if c == CR or c == LF or c == escape or is_del_start:
            if pos > start:
                out.append(char_seq[start:pos])
            esc_target = c
            if c == LF:
                esc_target = 'n'
            elif c == CR:
                esc_target = 'r'
            out.append(escape)
            out.append(esc_target)
            if is_del_start:
                for _ in range(1, delim_len):
                    pos += 1
                    out.append(escape)
                    out.append(char_seq[pos])
            start = pos + 1
        pos += 1
    if pos > start:
        out.append(char_seq[start:pos])
    return "".join(out)


def _print_with_quotes(object_val: Any, char_seq: str, format_config: CSVFormatConfig, new_record: bool) -> str:
    quote = False
    start = 0
    pos = 0
    length = len(char_seq)
    delim = format_config.delimiter
    delim_len = len(delim)
    quote_char = format_config.quote_char
    escape_char = format_config.escape_char if format_config.escape_char is not None else quote_char

    quote_mode = format_config.quote_mode
    if quote_mode is None:
        quote_mode = QuoteMode.MINIMAL

    if quote_mode in (QuoteMode.ALL, QuoteMode.ALL_NON_NULL):
        quote = True
    elif quote_mode == QuoteMode.NON_NUMERIC:
        quote = True
    elif quote_mode == QuoteMode.NONE:
        return _print_with_escapes(char_seq, format_config.escape_char, delim)
    elif quote_mode == QuoteMode.MINIMAL:
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
                    if c == LF or c == CR or c == quote_char or c == escape_char or _is_delimiter_at(char_seq, pos, delim):
                        quote = True
                        break
                    pos += 1
                if not quote:
                    c = char_seq[length - 1]
                    if ord(c) <= 0x0020:
                        quote = True
        if not quote:
            return char_seq
    else:
        raise IllegalArgumentException(f"Unexpected Quote value: {quote_mode}")

    if not quote:
        return char_seq

    out = [quote_char]
    pos = 0
    start = 0
    while pos < length:
        c = char_seq[pos]
        if c == quote_char or c == escape_char:
            out.append(char_seq[start:pos])
            out.append(escape_char)
            start = pos
        pos += 1
    out.append(char_seq[start:pos])
    out.append(quote_char)
    return "".join(out)


def print_csv(records: Any, config: Optional[dict] = None) -> str:
    format_config = CSVFormatConfig(config)
    if not hasattr(records, '__iter__'):
        raise IllegalArgumentException("records must be an iterable")

    out_parts = []

    for record in records:
        if not hasattr(record, '__iter__') or isinstance(record, (str, bytes)):
            raise IllegalArgumentException("each record must be an iterable of fields")

        record_items = list(record)
        for i, val in enumerate(record_items):
            new_record = (i == 0)
            if not new_record:
                out_parts.append(format_config.delimiter)

            if val is None:
                if format_config.null_string is None:
                    cs = ""
                elif format_config.quote_mode == QuoteMode.ALL:
                    cs = f"{format_config.quote_char}{format_config.null_string}{format_config.quote_char}"
                else:
                    cs = format_config.null_string
            elif isinstance(val, str):
                cs = val
            else:
                raise IllegalArgumentException("record field must be string or None")

            if format_config.trim:
                cs = _java_trim(cs)

            if val is None:
                out_parts.append(cs)
            elif format_config.quote_char is not None:
                out_parts.append(_print_with_quotes(val, cs, format_config, new_record))
            elif format_config.escape_char is not None:
                out_parts.append(_print_with_escapes(cs, format_config.escape_char, format_config.delimiter))
            else:
                out_parts.append(cs)

        if format_config.trailing_delimiter:
            out_parts.append(format_config.delimiter)
        if format_config.record_separator is not None:
            out_parts.append(format_config.record_separator)

    return "".join(out_parts)
