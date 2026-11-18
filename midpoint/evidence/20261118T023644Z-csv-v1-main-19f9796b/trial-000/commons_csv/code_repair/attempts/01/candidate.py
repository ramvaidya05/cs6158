import numbers

class CSVParseError(Exception):
    """Raised when an I/O or parsing error occurs in CSV processing."""
    pass

class IllegalArgumentException(Exception):
    """Raised when configuration parameters are invalid or inconsistent."""
    pass

CR = '\r'
LF = '\n'
CRLF = '\r\n'
COMMENT = '#'
SP = ' '
UNDEFINED = -2
END_OF_STREAM = -1
DISABLED = '\ufffe'

def _is_trim_char(c: str) -> bool:
    return ord(c) <= ord(SP)

def _trim(s: str) -> str:
    start = 0
    end = len(s)
    while start < end and _is_trim_char(s[start]):
        start += 1
    while end > start and _is_trim_char(s[end - 1]):
        end -= 1
    return s[start:end]

def _is_line_break(c: str) -> bool:
    return c == LF or c == CR

def _contains_line_break(s: str) -> bool:
    return CR in s or LF in s

class Format:
    def __init__(self, config=None):
        cfg = config or {}
        
        # Strict boolean validation
        bool_keys = ["ignore_empty_lines", "ignore_surrounding_spaces", "trim", "trailing_delimiter"]
        for k in bool_keys:
            if k in cfg and not isinstance(cfg[k], bool):
                raise IllegalArgumentException(f"{k} must be a boolean")

        self.delimiter = cfg.get("delimiter", ",")
        self.quote_char = cfg.get("quote", '"')
        self.escape_char = cfg.get("escape", None)
        self.record_separator = cfg.get("record_separator", CRLF)
        self.null_string = cfg.get("null_string", None)
        self.quote_mode = cfg.get("quote_mode", None)
        self.ignore_empty_lines = cfg.get("ignore_empty_lines", True)
        self.ignore_surrounding_spaces = cfg.get("ignore_surrounding_spaces", False)
        self.trim = cfg.get("trim", False)
        self.comment_marker = cfg.get("comment_marker", None)
        self.trailing_delimiter = cfg.get("trailing_delimiter", False)
        self.validate()

    def validate(self):
        if not isinstance(self.delimiter, str):
            raise IllegalArgumentException("Delimiter must be a string")
        if not self.delimiter:
            raise IllegalArgumentException("The delimiter cannot be empty")
        if _contains_line_break(self.delimiter):
            raise IllegalArgumentException("The delimiter cannot be a line break")
        if self.quote_char is not None:
            if not isinstance(self.quote_char, str) or len(self.quote_char) != 1:
                raise IllegalArgumentException("The quote character must be one character or null")
            if _is_line_break(self.quote_char):
                raise IllegalArgumentException("The quoteChar cannot be a line break")
            if self.quote_char in self.delimiter:
                raise IllegalArgumentException(f"The quoteChar character and the delimiter cannot be the same ('{self.quote_char}')")
        if self.escape_char is not None:
            if not isinstance(self.escape_char, str) or len(self.escape_char) != 1:
                raise IllegalArgumentException("The escape character must be one character or null")
            if _is_line_break(self.escape_char):
                raise IllegalArgumentException("The escape character cannot be a line break")
            if self.escape_char in self.delimiter:
                raise IllegalArgumentException(f"The escape character and the delimiter cannot be the same ('{self.escape_char}')")
        if self.comment_marker is not None:
            if not isinstance(self.comment_marker, str) or len(self.comment_marker) != 1:
                raise IllegalArgumentException("The comment marker must be one character or null")
            if _is_line_break(self.comment_marker):
                raise IllegalArgumentException("The comment start marker character cannot be a line break")
            if self.comment_marker in self.delimiter:
                raise IllegalArgumentException(f"The comment start character and the delimiter cannot be the same ('{self.comment_marker}')")
            if self.quote_char is not None and self.quote_char == self.comment_marker:
                raise IllegalArgumentException(f"The comment start character and the quoteChar cannot be the same ('{self.comment_marker}')")
            if self.escape_char is not None and self.escape_char == self.comment_marker:
                raise IllegalArgumentException(f"The comment start and the escape character cannot be the same ('{self.comment_marker}')")
        if self.escape_char is None and self.quote_mode == "NONE":
            raise IllegalArgumentException("No quotes mode set but no escape character is set")
        valid_quote_modes = (None, "ALL", "ALL_NON_NULL", "MINIMAL", "NON_NUMERIC", "NONE")
        if self.quote_mode not in valid_quote_modes:
            raise IllegalArgumentException(f"Unknown quote mode: {self.quote_mode}")
        if self.null_string is not None and not isinstance(self.null_string, str):
            raise IllegalArgumentException("null_string must be a string or null")
        if self.record_separator is not None and not isinstance(self.record_separator, str):
            raise IllegalArgumentException("record_separator must be a string or null")

class ExtendedBufferedReader:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)
        self.last_char = UNDEFINED
        self.eol_counter = 0
        self.position = 0

    def get_current_line_number(self) -> int:
        if self.last_char in (ord(CR), ord(LF), UNDEFINED, END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1

    def get_last_char(self) -> int:
        return self.last_char

    def get_position(self) -> int:
        return self.position

    def look_ahead(self, n: int = 1):
        if n == 1:
            if self.pos >= self.length:
                return END_OF_STREAM
            return ord(self.text[self.pos])
        buf = []
        for i in range(n):
            p = self.pos + i
            if p < self.length:
                buf.append(self.text[p])
            else:
                break
        return "".join(buf)

    def read(self) -> int:
        if self.pos >= self.length:
            current = END_OF_STREAM
        else:
            current = ord(self.text[self.pos])
            self.pos += 1
        if current == ord(CR) or (current == ord(LF) and self.last_char != ord(CR)) or \
           (current == END_OF_STREAM and self.last_char not in (ord(CR), ord(LF), END_OF_STREAM)):
            self.eol_counter += 1
        self.last_char = current
        self.position += 1
        return self.last_char

    def read_chars(self, length: int) -> str:
        if self.pos >= self.length:
            self.last_char = END_OF_STREAM
            return ""
        available = min(length, self.length - self.pos)
        chars = self.text[self.pos:self.pos + available]
        for i, ch in enumerate(chars):
            if ch == LF:
                prev = self.last_char if i == 0 else ord(chars[i - 1])
                if prev != ord(CR):
                    self.eol_counter += 1
            elif ch == CR:
                self.eol_counter += 1
        self.pos += available
        self.position += available
        if available > 0:
            self.last_char = ord(chars[-1])
        return chars

    def read_line(self):
        if self.look_ahead(1) == END_OF_STREAM:
            return None
        buf = []
        while True:
            c = self.read()
            if c == ord(CR):
                if self.look_ahead(1) == ord(LF):
                    self.read()
            if c in (END_OF_STREAM, ord(LF), ord(CR)):
                break
            buf.append(chr(c))
        return "".join(buf)

class Token:
    INVALID = 0
    TOKEN = 1
    EOF = 2
    EORECORD = 3
    COMMENT = 4

    def __init__(self):
        self.content = []
        self.type = Token.INVALID
        self.is_ready = False
        self.is_quoted = False

    def reset(self):
        self.content.clear()
        self.type = Token.INVALID
        self.is_ready = False
        self.is_quoted = False

class Lexer:
    def __init__(self, fmt: Format, reader: ExtendedBufferedReader):
        self.reader = reader
        self.delimiter = fmt.delimiter
        self.escape = ord(fmt.escape_char) if fmt.escape_char else ord(DISABLED)
        self.quote_char = ord(fmt.quote_char) if fmt.quote_char else ord(DISABLED)
        self.comment_start = ord(fmt.comment_marker) if fmt.comment_marker else ord(DISABLED)
        self.ignore_surrounding_spaces = fmt.ignore_surrounding_spaces
        self.ignore_empty_lines = fmt.ignore_empty_lines
        self.first_eol = None
        self.is_last_token_delimiter = False

    def is_closed(self) -> bool:
        return False

    def is_comment_start(self, ch: int) -> bool:
        return ch == self.comment_start

    def is_delimiter(self, ch: int) -> bool:
        self.is_last_token_delimiter = False
        if ch == END_OF_STREAM or ch != ord(self.delimiter[0]):
            return False
        if len(self.delimiter) == 1:
            self.is_last_token_delimiter = True
            return True
        rem_len = len(self.delimiter) - 1
        look = self.reader.look_ahead(rem_len)
        if len(look) < rem_len:
            return False
        for i in range(rem_len):
            if look[i] != self.delimiter[i + 1]:
                return False
        read_str = self.reader.read_chars(rem_len)
        self.is_last_token_delimiter = (len(read_str) == rem_len)
        return self.is_last_token_delimiter

    def is_end_of_file(self, ch: int) -> bool:
        return ch == END_OF_STREAM

    def is_escape(self, ch: int) -> bool:
        return ch == self.escape

    def is_escape_delimiter(self) -> bool:
        needed_len = 2 * len(self.delimiter) - 1
        buf = self.reader.look_ahead(needed_len)
        if len(buf) < needed_len:
            return False
        if buf[0] != self.delimiter[0]:
            return False
        for i in range(1, len(self.delimiter)):
            if ord(buf[2 * i - 1]) != self.escape or buf[2 * i] != self.delimiter[i]:
                return False
        read_str = self.reader.read_chars(needed_len)
        return len(read_str) == needed_len

    def is_meta_char(self, ch: int) -> bool:
        return ch == self.escape or ch == self.quote_char or ch == self.comment_start

    def is_quote_char(self, ch: int) -> bool:
        return ch == self.quote_char

    def is_start_of_line(self, ch: int) -> bool:
        return ch == ord(LF) or ch == ord(CR) or ch == UNDEFINED

    def next_token(self, token: Token) -> Token:
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
        if self.is_start_of_line(last_char) and self.is_comment_start(c):
            line = self.reader.read_line()
            if line is None:
                token.type = Token.EOF
                return token
            comment = line.strip()
            token.content.extend(list(comment))
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
            elif self.is_quote_char(c):
                self.parse_encapsulated_token(token)
            elif self.is_end_of_file(c):
                token.type = Token.EOF
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
                    token.content.extend(list(self.delimiter))
                else:
                    unescaped = self.read_escape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(chr(c))
                        token.content.append(chr(self.reader.get_last_char()))
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
                            token.type = Token.TOKEN
                            return token
                        if self.is_end_of_file(c):
                            token.type = Token.EOF
                            token.is_ready = True
                            return token
                        if self.read_end_of_line(c):
                            token.type = Token.EORECORD
                            return token
                        if c == END_OF_STREAM or not chr(c).isspace():
                            raise CSVParseError(f"(line {self.reader.get_current_line_number()}) invalid char between encapsulated token and delimiter")
            elif self.is_end_of_file(c):
                raise CSVParseError(f"(startline {start_line_number}) EOF reached before encapsulated token finished")
            else:
                token.content.append(chr(c))

    def parse_simple_token(self, token: Token, ch: int) -> Token:
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
            if self.is_escape(ch):
                if self.is_escape_delimiter():
                    token.content.extend(list(self.delimiter))
                else:
                    unescaped = self.read_escape()
                    if unescaped == END_OF_STREAM:
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

    def read_end_of_line(self, ch: int) -> bool:
        if ch == ord(CR) and self.reader.look_ahead(1) == ord(LF):
            ch = self.reader.read()
            if self.first_eol is None:
                self.first_eol = CRLF
        if self.first_eol is None:
            if ch == ord(LF):
                self.first_eol = LF
            elif ch == ord(CR):
                self.first_eol = CR
        return ch == ord(LF) or ch == ord(CR)

    def read_escape(self) -> int:
        ch = self.reader.read()
        if ch == ord('r'):
            return ord(CR)
        elif ch == ord('n'):
            return ord(LF)
        elif ch == ord('t'):
            return ord('\t')
        elif ch == ord('b'):
            return ord('\b')
        elif ch == ord('f'):
            return ord('\f')
        elif ch in (ord(CR), ord(LF), ord('\f'), ord('\t'), ord('\b')):
            return ch
        elif ch == END_OF_STREAM:
            raise CSVParseError("EOF whilst processing escape sequence")
        else:
            if self.is_meta_char(ch):
                return ch
            return END_OF_STREAM

    def trim_trailing_spaces(self, buffer: list):
        while buffer and chr(ord(buffer[-1])).isspace():
            buffer.pop()

class CSVParserInternal:
    def __init__(self, text: str, fmt: Format):
        self.format = fmt
        self.reader = ExtendedBufferedReader(text)
        self.lexer = Lexer(fmt, self.reader)
        self.reusable_token = Token()
        self.record_list = []

    def is_strict_quote_mode(self) -> bool:
        return self.format.quote_mode in ("ALL_NON_NULL", "NON_NUMERIC")

    def handle_null(self, input_val: str) -> str:
        is_quoted = self.reusable_token.is_quoted
        null_string = self.format.null_string
        strict_quote_mode = self.is_strict_quote_mode()
        if input_val == null_string:
            return input_val if (strict_quote_mode and is_quoted) else None
        if strict_quote_mode and null_string is None and input_val == "" and not is_quoted:
            return None
        return input_val

    def add_record_value(self, last_record: bool):
        raw_str = "".join(self.reusable_token.content)
        input_val = _trim(raw_str) if self.format.trim else raw_str
        if last_record and input_val == "" and self.format.trailing_delimiter:
            return
        self.record_list.append(self.handle_null(input_val))

    def next_record(self):
        self.record_list = []
        while True:
            self.reusable_token.reset()
            self.lexer.next_token(self.reusable_token)
            ttype = self.reusable_token.type
            if ttype == Token.TOKEN:
                self.add_record_value(False)
            elif ttype == Token.EORECORD:
                self.add_record_value(True)
                break
            elif ttype == Token.EOF:
                if self.reusable_token.is_ready:
                    self.add_record_value(True)
                break
            elif ttype == Token.INVALID:
                raise CSVParseError(f"(line {self.reader.get_current_line_number()}) invalid parse sequence")
            elif ttype == Token.COMMENT:
                self.reusable_token.type = Token.TOKEN
            else:
                raise CSVParseError(f"Unexpected Token type: {ttype}")
        if not self.record_list:
            return None
        return list(self.record_list)

    def get_records(self):
        records = []
        while True:
            rec = self.next_record()
            if rec is None:
                break
            records.append(rec)
        return records

def parse_csv(text: str, config: dict = None):
    fmt = Format(config)
    parser = CSVParserInternal(text, fmt)
    return parser.get_records()

def _is_delimiter_match(char_seq: str, start_index: int, delimiter: str) -> bool:
    if start_index + len(delimiter) > len(char_seq):
        return False
    return char_seq[start_index:start_index + len(delimiter)] == delimiter

def _print_with_escapes(char_seq: str, out: list, fmt: Format):
    start = 0
    pos = 0
    end = len(char_seq)
    delim = fmt.delimiter
    delim_len = len(delim)
    escape = fmt.escape_char
    while pos < end:
        c = char_seq[pos]
        is_delim_start = _is_delimiter_match(char_seq, pos, delim)
        if c in (CR, LF, escape) or is_delim_start:
            if pos > start:
                out.append(char_seq[start:pos])
            if c == LF:
                c = 'n'
            elif c == CR:
                c = 'r'
            out.append(escape)
            out.append(c)
            if is_delim_start:
                for _ in range(1, delim_len):
                    pos += 1
                    c = char_seq[pos]
                    out.append(escape)
                    out.append(c)
            start = pos + 1
        pos += 1
    if pos > start:
        out.append(char_seq[start:pos])

def _print_with_quotes(val_obj, char_seq: str, out: list, new_record: bool, fmt: Format):
    quote = False
    start = 0
    pos = 0
    length = len(char_seq)
    delim = fmt.delimiter
    delim_len = len(delim)
    quote_char = fmt.quote_char
    escape_char = fmt.escape_char if fmt.escape_char is not None else quote_char
    quote_mode_policy = fmt.quote_mode if fmt.quote_mode is not None else "MINIMAL"
    if quote_mode_policy in ("ALL", "ALL_NON_NULL"):
        quote = True
    elif quote_mode_policy == "NON_NUMERIC":
        quote = not isinstance(val_obj, numbers.Number) or isinstance(val_obj, bool)
    elif quote_mode_policy == "NONE":
        _print_with_escapes(char_seq, out, fmt)
        return
    elif quote_mode_policy == "MINIMAL":
        if length <= 0:
            if new_record:
                quote = True
        else:
            c = char_seq[0]
            if ord(c) <= ord(COMMENT):
                quote = True
            else:
                while pos < length:
                    c = char_seq[pos]
                    if c in (LF, CR, quote_char, escape_char) or _is_delimiter_match(char_seq, pos, delim):
                        quote = True
                        break
                    pos += 1
                if not quote:
                    pos = length - 1
                    c = char_seq[pos]
                    if _is_trim_char(c):
                        quote = True
        if not quote:
            out.append(char_seq)
            return
    else:
        raise IllegalArgumentException(f"Unexpected Quote value: {quote_mode_policy}")
    if not quote:
        out.append(char_seq)
        return
    out.append(quote_char)
    pos = 0
    start = 0
    while pos < length:
        c = char_seq[pos]
        if c in (quote_char, escape_char):
            out.append(char_seq[start:pos])
            out.append(escape_char)
            start = pos
        pos += 1
    out.append(char_seq[start:pos])
    out.append(quote_char)

def _print_value(value, out: list, new_record: bool, fmt: Format):
    if value is None:
        if fmt.null_string is None:
            char_sequence = ""
        elif fmt.quote_mode == "ALL":
            char_sequence = f"{fmt.quote_char}{fmt.null_string}{fmt.quote_char}"
        else:
            char_sequence = fmt.null_string
    elif isinstance(value, str):
        char_sequence = value
    else:
        char_sequence = str(value)
    char_sequence = _trim(char_sequence) if fmt.trim else char_sequence
    if not new_record:
        out.append(fmt.delimiter)
    if value is None:
        out.append(char_sequence)
    elif fmt.quote_char is not None:
        _print_with_quotes(value, char_sequence, out, new_record, fmt)
    elif fmt.escape_char is not None:
        _print_with_escapes(char_sequence, out, fmt)
    else:
        out.append(char_sequence)

def print_csv(records, config: dict = None) -> str:
    fmt = Format(config)
    out = []
    for rec in records:
        for i, val in enumerate(rec):
            _print_value(val, out, i == 0, fmt)
        if fmt.trailing_delimiter:
            out.append(fmt.delimiter)
        if fmt.record_separator is not None:
            out.append(fmt.record_separator)
    return "".join(out)
