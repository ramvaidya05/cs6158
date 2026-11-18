import io
from enum import Enum

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

class DuplicateHeaderMode(Enum):
    ALLOW_ALL = "ALLOW_ALL"
    ALLOW_EMPTY = "ALLOW_EMPTY"
    DISALLOW = "DISALLOW"

CR = '\r'
LF = '\n'
CRLF = "\r\n"
SP = ' '
COMMENT = '#'
BACKSPACE = '\b'
FF = '\f'
TAB = '\t'
END_OF_STREAM = -1
UNDEFINED = -2
DISABLED = '\ufffe'

def _is_line_break(c):
    return c in (LF, CR)

def _contains_line_break(s):
    return CR in s or LF in s

def _is_trim_char(ch):
    return ord(ch) <= ord(SP)

class CSVFormat:
    def __init__(self, delimiter=',', quote_char='"', quote_mode=None, comment_marker=None,
                 escape_character=None, ignore_surrounding_spaces=False, ignore_empty_lines=True,
                 record_separator=CRLF, null_string=None, header=None, header_comments=None,
                 skip_header_record=False, allow_missing_column_names=False, ignore_header_case=False,
                 trim=False, trailing_delimiter=False, auto_flush=False,
                 duplicate_header_mode=DuplicateHeaderMode.ALLOW_ALL):
        self.delimiter = delimiter
        self.quote_char = quote_char
        self.quote_mode = quote_mode
        self.comment_marker = comment_marker
        self.escape_character = escape_character
        self.ignore_surrounding_spaces = ignore_surrounding_spaces
        self.ignore_empty_lines = ignore_empty_lines
        self.record_separator = record_separator
        self.null_string = null_string
        self.header = list(header) if header is not None else None
        self.header_comments = list(header_comments) if header_comments is not None else None
        self.skip_header_record = skip_header_record
        self.allow_missing_column_names = allow_missing_column_names
        self.ignore_header_case = ignore_header_case
        self.trim = trim
        self.trailing_delimiter = trailing_delimiter
        self.auto_flush = auto_flush
        self.duplicate_header_mode = duplicate_header_mode
        self.validate()

    def validate(self):
        if not self.delimiter:
            raise IllegalArgumentException("The delimiter cannot be empty")
        if _contains_line_break(self.delimiter):
            raise IllegalArgumentException("The delimiter cannot be a line break")
        if self.quote_char is not None and self.quote_char in self.delimiter:
            raise IllegalArgumentException(f"The quoteChar character and the delimiter cannot be the same ('{self.quote_char}')")
        if self.escape_character is not None and self.escape_character in self.delimiter:
            raise IllegalArgumentException(f"The escape character and the delimiter cannot be the same ('{self.escape_character}')")
        if self.comment_marker is not None and self.comment_marker in self.delimiter:
            raise IllegalArgumentException(f"The comment start character and the delimiter cannot be the same ('{self.comment_marker}')")
        if self.quote_char is not None and self.quote_char == self.comment_marker:
            raise IllegalArgumentException(f"The comment start character and the quoteChar cannot be the same ('{self.comment_marker}')")
        if self.escape_character is not None and self.escape_character == self.comment_marker:
            raise IllegalArgumentException(f"The comment start and the escape character cannot be the same ('{self.comment_marker}')")
        if self.escape_character is None and self.quote_mode == QuoteMode.NONE:
            raise IllegalArgumentException("No quotes mode set but no escape character is set")

    def trim_str(self, val):
        if val is None:
            return None
        return val.strip() if self.trim else val

class ExtendedBufferedReader:
    def __init__(self, text):
        self.text = text
        self.length = len(text)
        self.index = 0
        self.last_char = UNDEFINED
        self.eol_counter = 0
        self.position = 0
        self.closed = False

    def close(self):
        self.closed = True
        self.last_char = END_OF_STREAM

    def get_current_line_number(self):
        if self.last_char in (ord(CR), ord(LF), UNDEFINED, END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1

    def get_position(self):
        return self.position

    def get_last_char(self):
        return self.last_char

    def is_closed(self):
        return self.closed

    def look_ahead(self, n=1):
        if self.index >= self.length:
            return END_OF_STREAM if n == 1 else []
        if n == 1:
            return ord(self.text[self.index])
        chars = [ord(c) for c in self.text[self.index : self.index + n]]
        return chars

    def read(self):
        if self.index >= self.length:
            current = END_OF_STREAM
        else:
            current = ord(self.text[self.index])
            self.index += 1

        if (current == ord(CR) or
            (current == ord(LF) and self.last_char != ord(CR)) or
            (current == END_OF_STREAM and self.last_char != ord(CR) and self.last_char != ord(LF) and self.last_char != END_OF_STREAM)):
            self.eol_counter += 1

        self.last_char = current
        if current != END_OF_STREAM:
            self.position += 1
        return self.last_char

    def read_chars(self, n):
        chars = []
        for _ in range(n):
            c = self.read()
            if c == END_OF_STREAM:
                break
            chars.append(c)
        return chars

    def read_line(self):
        if self.look_ahead() == END_OF_STREAM:
            return None
        buf = []
        while True:
            current = self.read()
            if current == ord(CR):
                nxt = self.look_ahead()
                if nxt == ord(LF):
                    self.read()
            if current == END_OF_STREAM or current == ord(LF) or current == ord(CR):
                break
            buf.append(chr(current))
        return "".join(buf)

class TokenType(Enum):
    INVALID = 0
    TOKEN = 1
    EOF = 2
    EORECORD = 3
    COMMENT = 4

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
    def __init__(self, format: CSVFormat, reader: ExtendedBufferedReader):
        self.format = format
        self.reader = reader
        self.delimiter = [ord(c) for c in format.delimiter]
        self.escape = ord(format.escape_character) if format.escape_character is not None else ord(DISABLED)
        self.quote_char = ord(format.quote_char) if format.quote_char is not None else ord(DISABLED)
        self.comment_start = ord(format.comment_marker) if format.comment_marker is not None else ord(DISABLED)
        self.ignore_surrounding_spaces = format.ignore_surrounding_spaces
        self.ignore_empty_lines = format.ignore_empty_lines
        self.first_eol = None
        self.is_last_token_delimiter = False

    def is_delimiter(self, ch):
        self.is_last_token_delimiter = False
        if ch != self.delimiter[0]:
            return False
        if len(self.delimiter) == 1:
            self.is_last_token_delimiter = True
            return True
        n = len(self.delimiter) - 1
        look = self.reader.look_ahead(n)
        if len(look) < n:
            return False
        for i in range(n):
            if look[i] != self.delimiter[i + 1]:
                return False
        self.reader.read_chars(n)
        self.is_last_token_delimiter = True
        return True

    def is_escape(self, ch):
        return ch == self.escape

    def is_quote_char(self, ch):
        return ch == self.quote_char

    def is_comment_start(self, ch):
        return ch == self.comment_start

    def is_start_of_line(self, ch):
        return ch == ord(LF) or ch == ord(CR) or ch == UNDEFINED

    def is_end_of_file(self, ch):
        return ch == END_OF_STREAM

    def is_meta_char(self, ch):
        return ch == self.escape or ch == self.quote_char or ch == self.comment_start

    def is_escape_delimiter(self):
        m = len(self.delimiter)
        look_len = 2 * m - 1
        look = self.reader.look_ahead(look_len)
        if len(look) < look_len:
            return False
        if look[0] != self.delimiter[0]:
            return False
        for i in range(1, m):
            if look[2 * i] != self.delimiter[i] or look[2 * i - 1] != self.escape:
                return False
        self.reader.read_chars(look_len)
        return True

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
        return ch == ord(LF) or ch == ord(CR)

    def read_escape(self):
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
            if self.is_meta_char(ch):
                return ch
            return END_OF_STREAM

    def trim_trailing_spaces(self, buf):
        while buf and chr(buf[-1]).isspace():
            buf.pop()

    def next_token(self, token: Token):
        last_char = self.reader.get_last_char()
        c = self.reader.read()
        eol = self.read_end_of_line(c)

        if self.ignore_empty_lines:
            while eol and self.is_start_of_line(last_char):
                last_char = c
                c = self.reader.read()
                eol = self.read_end_of_line(c)
                if self.is_end_of_file(c):
                    token.type = TokenType.EOF
                    return token

        if self.is_end_of_file(last_char) or (not self.is_last_token_delimiter and self.is_end_of_file(c)):
            token.type = TokenType.EOF
            return token

        if self.is_start_of_line(last_char) and self.is_comment_start(c):
            line = self.reader.read_line()
            if line is None:
                token.type = TokenType.EOF
                return token
            token.content.extend([ord(x) for x in line.strip()])
            token.type = TokenType.COMMENT
            return token

        while token.type == TokenType.INVALID:
            if self.ignore_surrounding_spaces:
                while chr(c).isspace() and not self.is_delimiter(c) and not eol:
                    c = self.reader.read()
                    eol = self.read_end_of_line(c)

            if self.is_delimiter(c):
                token.type = TokenType.TOKEN
            elif eol:
                token.type = TokenType.EORECORD
            elif self.is_quote_char(c):
                self.parse_encapsulated_token(token)
            elif self.is_end_of_file(c):
                token.type = TokenType.EOF
                token.is_ready = True
            else:
                self.parse_simple_token(token, c)
        return token

    def parse_encapsulated_token(self, token: Token):
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
                        last_c = self.reader.get_last_char()
                        if last_c != END_OF_STREAM:
                            token.content.append(c)
                            token.content.append(last_c)
                        else:
                            token.content.append(c)
                    else:
                        token.content.append(unescaped)
            elif self.is_quote_char(c):
                if self.is_quote_char(self.reader.look_ahead()):
                    c = self.reader.read()
                    token.content.append(c)
                else:
                    while True:
                        c = self.reader.read()
                        if self.is_delimiter(c):
                            token.type = TokenType.TOKEN
                            return token
                        if self.is_end_of_file(c):
                            token.type = TokenType.EOF
                            token.is_ready = True
                            return token
                        if self.read_end_of_line(c):
                            token.type = TokenType.EORECORD
                            return token
                        if not chr(c).isspace():
                            raise CSVParseError(f"(line {self.reader.get_current_line_number()}) invalid char between encapsulated token and delimiter")
            elif self.is_end_of_file(c):
                raise CSVParseError(f"(startline {start_line_number}) EOF reached before encapsulated token finished")
            else:
                token.content.append(c)

    def parse_simple_token(self, token: Token, ch):
        while True:
            if self.read_end_of_line(ch):
                token.type = TokenType.EORECORD
                break
            if self.is_end_of_file(ch):
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
                        last_c = self.reader.get_last_char()
                        if last_c != END_OF_STREAM:
                            token.content.append(ch)
                            token.content.append(last_c)
                        else:
                            token.content.append(ch)
                    else:
                        token.content.append(unescaped)
            else:
                token.content.append(ch)
            ch = self.reader.read()

        if self.ignore_surrounding_spaces:
            self.trim_trailing_spaces(token.content)
        return token

class CSVParser:
    def __init__(self, text: str, format: CSVFormat):
        self.format = format
        self.reader = ExtendedBufferedReader(text)
        self.lexer = Lexer(format, self.reader)
        self.reusable_token = Token()
        self.record_list = []

    def _handle_null(self, input_val):
        is_quoted = self.reusable_token.is_quoted
        null_string = self.format.null_string
        strict_quote_mode = self.format.quote_mode in (QuoteMode.ALL_NON_NULL, QuoteMode.NON_NUMERIC)
        if input_val == null_string:
            return input_val if (strict_quote_mode and is_quoted) else None
        if strict_quote_mode and null_string is None and input_val == "" and not is_quoted:
            return None
        return input_val

    def _add_record_value(self, last_record):
        raw = "".join(chr(c) for c in self.reusable_token.content)
        input_val = self.format.trim_str(raw)
        if last_record and input_val == "" and self.format.trailing_delimiter:
            return
        self.record_list.append(self._handle_null(input_val))

    def parse_all(self):
        records = []
        while True:
            self.record_list = []
            while True:
                self.reusable_token.reset()
                self.lexer.next_token(self.reusable_token)
                if self.reusable_token.type == TokenType.TOKEN:
                    self._add_record_value(False)
                elif self.reusable_token.type == TokenType.EORECORD:
                    self._add_record_value(True)
                    break
                elif self.reusable_token.type == TokenType.EOF:
                    if self.reusable_token.is_ready:
                        self._add_record_value(True)
                    break
                elif self.reusable_token.type == TokenType.COMMENT:
                    self.reusable_token.type = TokenType.TOKEN
                else:
                    raise CSVParseError(f"(line {self.reader.get_current_line_number()}) invalid parse sequence")
            if self.record_list:
                records.append(list(self.record_list))
            if self.reusable_token.type == TokenType.EOF:
                break
        return records

def _build_format(config):
    cfg = dict(config or {})
    delimiter = cfg.get("delimiter", ",")
    if not isinstance(delimiter, str) or len(delimiter) != 1:
        raise IllegalArgumentException("delimiter must be a single UTF-16 character")
    
    quote_char = cfg.get("quote", '"')
    if quote_char is not None and (not isinstance(quote_char, str) or len(quote_char) != 1):
        raise IllegalArgumentException("quote must be one character or null")

    escape_char = cfg.get("escape", None)
    if escape_char is not None and (not isinstance(escape_char, str) or len(escape_char) != 1):
        raise IllegalArgumentException("escape must be one character or null")

    record_separator = cfg.get("record_separator", CRLF)
    if not isinstance(record_separator, str):
        raise IllegalArgumentException("record_separator must be a string")

    null_string = cfg.get("null_string", None)
    if null_string is not None and not isinstance(null_string, str):
        raise IllegalArgumentException("null_string must be a string or null")

    qm = cfg.get("quote_mode", None)
    if isinstance(qm, str):
        try:
            quote_mode = QuoteMode[qm]
        except KeyError:
            raise IllegalArgumentException(f"Unknown quote_mode {qm}")
    elif isinstance(qm, QuoteMode) or qm is None:
        quote_mode = qm
    else:
        raise IllegalArgumentException("Invalid quote_mode")

    def get_bool(key, default):
        if key in cfg:
            val = cfg[key]
            if not isinstance(val, bool):
                raise IllegalArgumentException(f"{key} must be a boolean")
            return val
        return default

    ignore_empty_lines = get_bool("ignore_empty_lines", True)
    ignore_surrounding_spaces = get_bool("ignore_surrounding_spaces", False)
    trim = get_bool("trim", False)

    return CSVFormat(
        delimiter=delimiter,
        quote_char=quote_char,
        quote_mode=quote_mode,
        escape_character=escape_char,
        record_separator=record_separator,
        null_string=null_string,
        ignore_empty_lines=ignore_empty_lines,
        ignore_surrounding_spaces=ignore_surrounding_spaces,
        trim=trim
    )

def parse_csv(text, config):
    if text is None or not isinstance(text, str):
        raise IllegalArgumentException("text must not be null and must be a string")
    format = _build_format(config)
    parser = CSVParser(text, format)
    return parser.parse_all()

class CSVPrinter:
    def __init__(self, out: io.StringIO, format: CSVFormat):
        self.out = out
        self.format = format
        self.new_record = True

    def print_with_escapes(self, char_seq: str):
        start = 0
        pos = 0
        length = len(char_seq)
        delim = self.format.delimiter
        delim_len = len(delim)
        escape = self.format.escape_character

        while pos < length:
            c = char_seq[pos]
            is_delim_start = char_seq.startswith(delim, pos)
            if c == CR or c == LF or c == escape or is_delim_start:
                if pos > start:
                    self.out.write(char_seq[start:pos])
                if c == LF:
                    c = 'n'
                elif c == CR:
                    c = 'r'
                self.out.write(escape)
                self.out.write(c)
                if is_delim_start:
                    for _ in range(1, delim_len):
                        pos += 1
                        c = char_seq[pos]
                        self.out.write(escape)
                        self.out.write(c)
                start = pos + 1
            pos += 1
        if pos > start:
            self.out.write(char_seq[start:pos])

    def print_with_quotes(self, object_val, char_seq: str, new_record: bool):
        quote = False
        length = len(char_seq)
        delim = self.format.delimiter
        quote_char = self.format.quote_char
        escape_char = self.format.escape_character if self.format.escape_character is not None else quote_char
        qm = self.format.quote_mode if self.format.quote_mode is not None else QuoteMode.MINIMAL

        if qm in (QuoteMode.ALL, QuoteMode.ALL_NON_NULL):
            quote = True
        elif qm == QuoteMode.NON_NUMERIC:
            is_num = isinstance(object_val, (int, float)) and not isinstance(object_val, bool)
            quote = not is_num
        elif qm == QuoteMode.NONE:
            self.print_with_escapes(char_seq)
            return
        elif qm == QuoteMode.MINIMAL:
            if length <= 0:
                if new_record:
                    quote = True
            else:
                c = char_seq[0]
                if ord(c) <= ord(COMMENT):
                    quote = True
                else:
                    pos = 0
                    while pos < length:
                        c = char_seq[pos]
                        if c == LF or c == CR or c == quote_char or c == escape_char or char_seq.startswith(delim, pos):
                            quote = True
                            break
                        pos += 1
                    if not quote:
                        c = char_seq[-1]
                        if _is_trim_char(c):
                            quote = True
        else:
            raise IllegalArgumentException(f"Unexpected Quote value: {qm}")

        if not quote:
            self.out.write(char_seq)
            return

        self.out.write(quote_char)
        start = 0
        pos = 0
        while pos < length:
            c = char_seq[pos]
            if c == quote_char or c == escape_char:
                self.out.write(char_seq[start:pos])
                self.out.write(escape_char)
                start = pos
            pos += 1
        self.out.write(char_seq[start:pos])
        self.out.write(quote_char)

    def print_value(self, value):
        if value is None:
            if self.format.null_string is None:
                char_sequence = ""
            elif self.format.quote_mode == QuoteMode.ALL:
                q = self.format.quote_char if self.format.quote_char is not None else ""
                char_sequence = f"{q}{self.format.null_string}{q}"
            else:
                char_sequence = self.format.null_string
        else:
            char_sequence = str(value)

        if self.format.trim:
            char_sequence = char_sequence.strip()

        if not self.new_record:
            self.out.write(self.format.delimiter)

        if value is None:
            self.out.write(char_sequence)
        elif self.format.quote_char is not None:
            self.print_with_quotes(value, char_sequence, self.new_record)
        elif self.format.escape_character is not None:
            self.print_with_escapes(char_sequence)
        else:
            self.out.write(char_sequence)

        self.new_record = False

    def println(self):
        if self.format.trailing_delimiter:
            self.out.write(self.format.delimiter)
        if self.format.record_separator is not None:
            self.out.write(self.format.record_separator)
        self.new_record = True

    def print_record(self, values):
        for val in values:
            self.print_value(val)
        self.println()

def print_csv(records, config):
    if records is None:
        raise IllegalArgumentException("records must not be null")
    format = _build_format(config)
    out = io.StringIO()
    printer = CSVPrinter(out, format)
    for record in records:
        printer.print_record(record)
    return out.getvalue()
