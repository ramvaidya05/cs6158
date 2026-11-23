import io
import unicodedata


class CSVParseError(Exception):
    """Exception raised when parsing CSV data fails (maps to IOException/UncheckedIOException)."""
    pass


class IllegalArgumentException(Exception):
    """Exception raised when invalid arguments or configuration settings are provided."""
    pass


# Constants
CR = '\r'
LF = '\n'
CRLF = '\r\n'
SP = ' '
TAB = '\t'
BACKSPACE = '\b'
FF = '\f'
END_OF_STREAM = -1
UNDEFINED = -2
DISABLED = '\ufffe'
COMMENT_CHAR = '#'
DOUBLE_QUOTE_CHAR = '"'


def is_java_whitespace(ch: str) -> bool:
    """Emulate java.lang.Character.isWhitespace(char)."""
    cp = ord(ch)
    if (0x1C <= cp <= 0x1F) or (0x09 <= cp <= 0x0D):
        return True
    cat = unicodedata.category(ch)
    if cat == 'Zs':
        # Exclude non-breaking spaces: 0x00A0, 0x2007, 0x202F
        return cp not in (0x00A0, 0x2007, 0x202F)
    return cat in ('Zl', 'Zp')


def java_trim(s: str) -> str:
    """Emulate Java String.trim(): removes characters <= '\u0020'."""
    start = 0
    end = len(s)
    while start < end and ord(s[start]) <= 0x20:
        start += 1
    while end > start and ord(s[end - 1]) <= 0x20:
        end -= 1
    return s[start:end]


def validate_char_unit(name: str, val, allow_none: bool = False):
    if val is None:
        if allow_none:
            return None
        raise IllegalArgumentException(f"{name} cannot be null")
    if not isinstance(val, str):
        raise IllegalArgumentException(f"{name} must be a string character")
    utf16_bytes = val.encode('utf-16-be')
    if len(utf16_bytes) != 2:
        raise IllegalArgumentException(f"{name} must be exactly one UTF-16 code unit")
    return val


def validate_boolean(name: str, val, default: bool) -> bool:
    if val is None:
        return default
    if type(val) is not bool:
        raise IllegalArgumentException(f"{name} must be a boolean")
    return val


class ExtendedBufferedReader:
    def __init__(self, reader):
        self.reader = reader
        self.last_char = UNDEFINED
        self.eol_counter = 0
        self.position = 0
        self.closed = False
        self.lookahead_buf = []

    def close(self):
        self.closed = True
        self.last_char = END_OF_STREAM

    def get_current_line_number(self):
        if self.last_char in (ord(CR), ord(LF), UNDEFINED, END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1

    def get_last_char(self):
        return self.last_char

    def get_position(self):
        return self.position

    def is_closed(self):
        return self.closed

    def _fill_lookahead(self, n):
        while len(self.lookahead_buf) < n:
            c = self.reader.read(1)
            if not c:
                break
            self.lookahead_buf.append(ord(c))

    def look_ahead(self, n=1):
        if isinstance(n, int):
            if n == 1:
                self._fill_lookahead(1)
                return self.lookahead_buf[0] if self.lookahead_buf else END_OF_STREAM
            self._fill_lookahead(n)
            return [self.lookahead_buf[i] if i < len(self.lookahead_buf) else END_OF_STREAM for i in range(n)]
        elif isinstance(n, list):
            req = len(n)
            self._fill_lookahead(req)
            for i in range(req):
                n[i] = self.lookahead_buf[i] if i < len(self.lookahead_buf) else END_OF_STREAM
            return n

    def read(self):
        if self.lookahead_buf:
            current = self.lookahead_buf.pop(0)
        else:
            c = self.reader.read(1)
            current = ord(c) if c else END_OF_STREAM

        if (current == ord(CR) or (current == ord(LF) and self.last_char != ord(CR))
                or (current == END_OF_STREAM and self.last_char != ord(CR) and self.last_char != ord(LF) and self.last_char != END_OF_STREAM)):
            self.eol_counter += 1

        self.last_char = current
        self.position += 1
        return self.last_char

    def read_buf(self, length):
        res = []
        for _ in range(length):
            c = self.read()
            if c == END_OF_STREAM:
                break
            res.append(c)
        return res

    def read_line(self):
        if self.look_ahead(1) == END_OF_STREAM:
            return None
        buffer = []
        while True:
            current = self.read()
            if current == ord(CR):
                next_ch = self.look_ahead(1)
                if next_ch == ord(LF):
                    self.read()
            if current in (END_OF_STREAM, ord(LF), ord(CR)):
                break
            buffer.append(chr(current))
        return "".join(buffer)


class Token:
    INVALID = 0
    TOKEN = 1
    EOF = 2
    EORECORD = 3
    COMMENT = 4

    def __init__(self):
        self.type = Token.INVALID
        self.content = []
        self.is_ready = False
        self.is_quoted = False

    def reset(self):
        self.content.clear()
        self.type = Token.INVALID
        self.is_ready = False
        self.is_quoted = False


class Lexer:
    def __init__(self, fmt, reader: ExtendedBufferedReader):
        self.reader = reader
        self.delimiter = [ord(c) for c in fmt['delimiter']]
        self.escape = ord(fmt['escape']) if fmt['escape'] is not None else ord(DISABLED)
        self.quote_char = ord(fmt['quote']) if fmt['quote'] is not None else ord(DISABLED)
        self.comment_start = ord(fmt['comment_marker']) if fmt.get('comment_marker') is not None else ord(DISABLED)
        self.ignore_surrounding_spaces = fmt['ignore_surrounding_spaces']
        self.ignore_empty_lines = fmt['ignore_empty_lines']
        self.delimiter_buf = [0] * (len(self.delimiter) - 1)
        self.escape_delimiter_buf = [0] * (2 * len(self.delimiter) - 1)
        self.first_eol = None
        self.is_last_token_delimiter = False

    def get_character_position(self):
        return self.reader.get_position()

    def get_current_line_number(self):
        return self.reader.get_current_line_number()

    def is_comment_start(self, ch):
        return ch == self.comment_start

    def is_delimiter(self, ch):
        self.is_last_token_delimiter = False
        if ch != self.delimiter[0]:
            return False
        if len(self.delimiter) == 1:
            self.is_last_token_delimiter = True
            return True
        self.reader.look_ahead(self.delimiter_buf)
        for i in range(len(self.delimiter_buf)):
            if self.delimiter_buf[i] != self.delimiter[i + 1]:
                return False
        buf_read = self.reader.read_buf(len(self.delimiter_buf))
        self.is_last_token_delimiter = len(buf_read) == len(self.delimiter_buf)
        return self.is_last_token_delimiter

    def is_end_of_file(self, ch):
        return ch == END_OF_STREAM

    def is_escape(self, ch):
        return ch == self.escape

    def is_escape_delimiter(self):
        self.reader.look_ahead(self.escape_delimiter_buf)
        if self.escape_delimiter_buf[0] != self.delimiter[0]:
            return False
        for i in range(1, len(self.delimiter)):
            if self.escape_delimiter_buf[2 * i] != self.delimiter[i] or self.escape_delimiter_buf[2 * i - 1] != self.escape:
                return False
        buf_read = self.reader.read_buf(len(self.escape_delimiter_buf))
        return len(buf_read) == len(self.escape_delimiter_buf)

    def is_meta_char(self, ch):
        return ch in (self.escape, self.quote_char, self.comment_start)

    def is_quote_char(self, ch):
        return ch == self.quote_char

    def is_start_of_line(self, ch):
        return ch in (ord(LF), ord(CR), UNDEFINED)

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
                while c != END_OF_STREAM and is_java_whitespace(chr(c)) and not self.is_delimiter(c) and not eol:
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

    def parse_encapsulated_token(self, token: Token):
        token.is_quoted = True
        start_line_number = self.get_current_line_number()
        while True:
            c = self.reader.read()
            if self.is_escape(c):
                if self.is_escape_delimiter():
                    token.content.extend(chr(x) for x in self.delimiter)
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
                        if not (c != END_OF_STREAM and is_java_whitespace(chr(c))):
                            raise CSVParseError(f"(line {self.get_current_line_number()}) invalid char between encapsulated token and delimiter")
            elif self.is_end_of_file(c):
                raise CSVParseError(f"(startline {start_line_number}) EOF reached before encapsulated token finished")
            else:
                token.content.append(chr(c))

    def parse_simple_token(self, token: Token, ch):
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
                    token.content.extend(chr(x) for x in self.delimiter)
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

    def read_end_of_line(self, ch):
        if ch == ord(CR) and self.reader.look_ahead(1) == ord(LF):
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

    def trim_trailing_spaces(self, buffer):
        length = len(buffer)
        while length > 0 and is_java_whitespace(buffer[length - 1]):
            length -= 1
        del buffer[length:]


def _build_validated_config(config: dict) -> dict:
    cfg = dict(config) if config else {}
    delimiter = validate_char_unit('delimiter', cfg.get('delimiter', ','))
    quote = validate_char_unit('quote', cfg.get('quote', '"'), allow_none=True)
    escape = validate_char_unit('escape', cfg.get('escape', None), allow_none=True)
    record_separator = cfg.get('record_separator', CRLF)
    if record_separator is not None and not isinstance(record_separator, str):
        raise IllegalArgumentException("record_separator must be a string or null")

    null_string = cfg.get('null_string', None)
    if null_string is not None and not isinstance(null_string, str):
        raise IllegalArgumentException("null_string must be a string or null")

    quote_mode = cfg.get('quote_mode', None)
    valid_quote_modes = ('ALL', 'ALL_NON_NULL', 'MINIMAL', 'NON_NUMERIC', 'NONE', None)
    if quote_mode not in valid_quote_modes:
        raise IllegalArgumentException(f"Invalid quote_mode: {quote_mode}")

    ignore_empty_lines = validate_boolean('ignore_empty_lines', cfg.get('ignore_empty_lines', True), True)
    ignore_surrounding_spaces = validate_boolean('ignore_surrounding_spaces', cfg.get('ignore_surrounding_spaces', False), False)
    trim = validate_boolean('trim', cfg.get('trim', False), False)
    trailing_delimiter = validate_boolean('trailing_delimiter', cfg.get('trailing_delimiter', False), False)

    # Java CSVFormat.setEscape / setQuote / validate line break checks
    if quote in (CR, LF):
        raise IllegalArgumentException("The quoteChar cannot be a line break")
    if escape in (CR, LF):
        raise IllegalArgumentException("The escape character cannot be a line break")
    if CR in delimiter or LF in delimiter:
        raise IllegalArgumentException("The delimiter cannot be a line break")
    if quote is not None and quote in delimiter:
        raise IllegalArgumentException(f"The quoteChar character and the delimiter cannot be the same ('{quote}')")
    if escape is not None and escape in delimiter:
        raise IllegalArgumentException(f"The escape character and the delimiter cannot be the same ('{escape}')")
    if escape is None and quote_mode == 'NONE':
        raise IllegalArgumentException("No quotes mode set but no escape character is set")

    return {
        'delimiter': delimiter,
        'quote': quote,
        'escape': escape,
        'record_separator': record_separator,
        'null_string': null_string,
        'quote_mode': quote_mode,
        'ignore_empty_lines': ignore_empty_lines,
        'ignore_surrounding_spaces': ignore_surrounding_spaces,
        'trim': trim,
        'trailing_delimiter': trailing_delimiter,
        'comment_marker': None,
    }


def parse_csv(text: str, config: dict = None) -> list:
    if not isinstance(text, str):
        raise IllegalArgumentException("text must be a string")
    fmt = _build_validated_config(config or {})
    reader = ExtendedBufferedReader(io.StringIO(text))
    lexer = Lexer(fmt, reader)
    reusable_token = Token()
    records = []
    record_list = []

    def is_strict_quote_mode():
        return fmt['quote_mode'] in ('ALL_NON_NULL', 'NON_NUMERIC')

    def handle_null(inp: str, is_quoted: bool):
        null_string = fmt['null_string']
        strict = is_strict_quote_mode()
        if inp == null_string:
            return inp if (strict and is_quoted) else None
        if strict and null_string is None and inp == "" and not is_quoted:
            return None
        return inp

    def add_record_value(last_record: bool):
        raw_token_str = "".join(reusable_token.content)
        inp = java_trim(raw_token_str) if fmt['trim'] else raw_token_str
        if last_record and inp == "" and fmt['trailing_delimiter']:
            return
        record_list.append(handle_null(inp, reusable_token.is_quoted))

    while True:
        record_list = []
        while True:
            reusable_token.reset()
            try:
                lexer.next_token(reusable_token)
            except CSVParseError:
                raise
            except Exception as e:
                raise CSVParseError(str(e)) from e

            tt = reusable_token.type
            if tt == Token.TOKEN:
                add_record_value(False)
            elif tt == Token.EORECORD:
                add_record_value(True)
                break
            elif tt == Token.EOF:
                if reusable_token.is_ready:
                    add_record_value(True)
                break
            elif tt == Token.INVALID:
                raise CSVParseError(f"(line {lexer.get_current_line_number()}) invalid parse sequence")
            elif tt == Token.COMMENT:
                reusable_token.type = Token.TOKEN
            else:
                raise CSVParseError(f"Unexpected Token type: {tt}")

        if record_list:
            records.append(record_list)
        if reusable_token.type == Token.EOF:
            break

    return records


def _is_delimiter(ch: str, seq: str, start_index: int, delim: str) -> bool:
    if ch != delim[0]:
        return False
    delim_len = len(delim)
    if start_index + delim_len > len(seq):
        return False
    return seq[start_index:start_index + delim_len] == delim


def _print_with_escapes(char_seq: str, out: io.StringIO, fmt: dict):
    start = 0
    pos = 0
    end = len(char_seq)
    delim = fmt['delimiter']
    delim_len = len(delim)
    escape = fmt['escape']
    while pos < end:
        c = char_seq[pos]
        is_delim_start = _is_delimiter(c, char_seq, pos, delim)
        if c == CR or c == LF or c == escape or is_delim_start:
            if pos > start:
                out.write(char_seq[start:pos])
            if c == LF:
                c = 'n'
            elif c == CR:
                c = 'r'
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


def _print_with_quotes(object_val, char_seq: str, out: io.StringIO, new_record: bool, fmt: dict):
    quote = False
    start = 0
    pos = 0
    length = len(char_seq)
    delim = fmt['delimiter']
    delim_len = len(delim)
    quote_char = fmt['quote']
    escape_char = fmt['escape'] if fmt['escape'] is not None else quote_char
    quote_mode = fmt['quote_mode'] or 'MINIMAL'

    if quote_mode in ('ALL', 'ALL_NON_NULL'):
        quote = True
    elif quote_mode == 'NON_NUMERIC':
        quote = not isinstance(object_val, (int, float))
    elif quote_mode == 'NONE':
        _print_with_escapes(char_seq, out, fmt)
        return
    elif quote_mode == 'MINIMAL':
        if length <= 0:
            if new_record:
                quote = True
        else:
            c = char_seq[0]
            if ord(c) <= ord(COMMENT_CHAR):
                quote = True
            else:
                while pos < length:
                    c = char_seq[pos]
                    if c == LF or c == CR or c == quote_char or c == escape_char or _is_delimiter(c, char_seq, pos, delim):
                        quote = True
                        break
                    pos += 1
                if not quote:
                    pos = length - 1
                    c = char_seq[pos]
                    if ord(c) <= ord(SP):
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
    pos = 0
    while pos < length:
        c = char_seq[pos]
        if c == quote_char or c == escape_char:
            out.write(char_seq[start:pos])
            out.write(escape_char)
            start = pos
        pos += 1
    out.write(char_seq[start:pos])
    out.write(quote_char)


def print_csv(records, config: dict = None) -> str:
    if not isinstance(records, (list, tuple)):
        raise IllegalArgumentException("records must be a sequence of records")
    fmt = _build_validated_config(config or {})
    out = io.StringIO()

    for record in records:
        if not isinstance(record, (list, tuple)):
            raise IllegalArgumentException("Each record must be a list or tuple of fields")
        new_record = True
        for val in record:
            if not new_record:
                out.write(fmt['delimiter'])

            # Resolve charSequence
            if val is None:
                if fmt['null_string'] is None:
                    char_seq = ""
                elif fmt['quote_mode'] == 'ALL':
                    quote_ch = fmt['quote'] if fmt['quote'] is not None else ""
                    char_seq = f"{quote_ch}{fmt['null_string']}{quote_ch}"
                else:
                    char_seq = fmt['null_string']
            else:
                if not isinstance(val, str):
                    raise IllegalArgumentException("Record values must be strings or null")
                char_seq = val

            if fmt['trim']:
                char_seq = java_trim(char_seq)

            if val is None:
                out.write(char_seq)
            elif fmt['quote'] is not None:
                _print_with_quotes(val, char_seq, out, new_record, fmt)
            elif fmt['escape'] is not None:
                _print_with_escapes(char_seq, out, fmt)
            else:
                out.write(char_seq)

            new_record = False

        # println
        if fmt['trailing_delimiter']:
            out.write(fmt['delimiter'])
        if fmt['record_separator'] is not None:
            out.write(fmt['record_separator'])

    return out.getvalue()
