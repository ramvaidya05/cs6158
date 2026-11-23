import unicodedata


class CSVParseError(Exception):
    """Raised when CSV parsing encounters an I/O or malformed syntax error."""
    pass


class IllegalArgumentException(Exception):
    """Raised when format configuration or arguments are invalid."""
    pass


CR = '\r'
LF = '\n'
CRLF = '\r\n'
COMMENT = '#'
DISABLED = '\ufffe'
END_OF_STREAM = -1
UNDEFINED = -2
SP = ' '


def _is_java_whitespace(ch):
    if not ch:
        return False
    cp = ord(ch)
    if cp in (0x0009, 0x000A, 0x000B, 0x000C, 0x000D, 0x001C, 0x001D, 0x001E, 0x001F, 0x0020):
        return True
    cat = unicodedata.category(ch)
    if cat in ('Zs', 'Zl', 'Zp'):
        if cp not in (0x00A0, 0x2007, 0x202F):
            return True
    return False


def _java_trim(s):
    if s is None:
        return None
    start = 0
    end = len(s)
    while start < end and ord(s[start]) <= 0x0020:
        start += 1
    while end > start and ord(s[end - 1]) <= 0x0020:
        end -= 1
    return s[start:end]


def _validate_utf16_char(val, name, allow_none=False):
    if val is None:
        if allow_none:
            return None
        raise IllegalArgumentException(f"{name} cannot be None")
    if not isinstance(val, str):
        raise IllegalArgumentException(f"{name} must be a string")
    encoded = val.encode('utf-16-le')
    if len(encoded) != 2:
        raise IllegalArgumentException(f"{name} must be exactly one UTF-16 code unit")
    return val


def _validate_bool(val, name):
    if not isinstance(val, bool):
        raise IllegalArgumentException(f"{name} must be a boolean")
    return val


class _Format:
    def __init__(self, config):
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise IllegalArgumentException("config must be a dictionary")

        raw_delim = config.get('delimiter', ',')
        self.delimiter = _validate_utf16_char(raw_delim, 'delimiter', allow_none=False)
        if self.delimiter in (CR, LF):
            raise IllegalArgumentException("The delimiter cannot be a line break")

        raw_quote = config.get('quote', '"')
        self.quote = _validate_utf16_char(raw_quote, 'quote', allow_none=True)
        if self.quote is not None and self.quote in (CR, LF):
            raise IllegalArgumentException("The quoteChar cannot be a line break")

        raw_escape = config.get('escape', None)
        self.escape = _validate_utf16_char(raw_escape, 'escape', allow_none=True)
        if self.escape is not None and self.escape in (CR, LF):
            raise IllegalArgumentException("The escape character cannot be a line break")

        raw_record_sep = config.get('record_separator', CRLF)
        if raw_record_sep is not None and not isinstance(raw_record_sep, str):
            raise IllegalArgumentException("record_separator must be a string or None")
        self.record_separator = raw_record_sep

        raw_null_str = config.get('null_string', None)
        if raw_null_str is not None and not isinstance(raw_null_str, str):
            raise IllegalArgumentException("null_string must be a string or None")
        self.null_string = raw_null_str

        raw_quote_mode = config.get('quote_mode', None)
        if raw_quote_mode is not None:
            if raw_quote_mode not in ('ALL', 'ALL_NON_NULL', 'MINIMAL', 'NON_NUMERIC', 'NONE'):
                raise IllegalArgumentException(f"Invalid quote_mode: {raw_quote_mode}")
        self.quote_mode = raw_quote_mode

        self.ignore_empty_lines = _validate_bool(config.get('ignore_empty_lines', True), 'ignore_empty_lines')
        self.ignore_surrounding_spaces = _validate_bool(config.get('ignore_surrounding_spaces', False), 'ignore_surrounding_spaces')
        self.trim = _validate_bool(config.get('trim', False), 'trim')

        self.comment_marker = None

        if self.quote is not None and self.delimiter == self.quote:
            raise IllegalArgumentException(f"The quoteChar character and the delimiter cannot be the same ('{self.quote}')")
        if self.escape is not None and self.delimiter == self.escape:
            raise IllegalArgumentException(f"The escape character and the delimiter cannot be the same ('{self.escape}')")
        if self.escape is None and self.quote_mode == 'NONE':
            raise IllegalArgumentException("No quotes mode set but no escape character is set")

        if self.quote is not None and self.null_string is not None:
            self.quoted_null_string = self.quote + self.null_string + self.quote
        else:
            self.quoted_null_string = None


class _ExtendedBufferedReader:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)
        self.last_char = UNDEFINED
        self.eol_counter = 0
        self.position = 0
        self.closed = False

    def read(self):
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

    def look_ahead(self):
        if self.pos >= self.length:
            return END_OF_STREAM
        return ord(self.text[self.pos])

    def look_ahead_n(self, n):
        res = []
        for i in range(n):
            p = self.pos + i
            if p < self.length:
                res.append(ord(self.text[p]))
            else:
                break
        return res

    def read_chars(self, n):
        chars_read = 0
        while chars_read < n and self.pos < self.length:
            self.read()
            chars_read += 1
        return chars_read != 0

    def get_last_char(self):
        return self.last_char

    def get_current_line_number(self):
        if self.last_char in (ord(CR), ord(LF), UNDEFINED, END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1


TOKEN_TYPE_INVALID = 0
TOKEN_TYPE_TOKEN = 1
TOKEN_TYPE_EOF = 2
TOKEN_TYPE_EORECORD = 3
TOKEN_TYPE_COMMENT = 4


class _Token:
    def __init__(self):
        self.type = TOKEN_TYPE_INVALID
        self.content = []
        self.is_ready = False
        self.is_quoted = False

    def reset(self):
        self.content.clear()
        self.type = TOKEN_TYPE_INVALID
        self.is_ready = False
        self.is_quoted = False


class _Lexer:
    def __init__(self, fmt, reader):
        self.format = fmt
        self.reader = reader
        self.delimiter = [ord(c) for c in fmt.delimiter]
        self.escape = ord(fmt.escape) if fmt.escape is not None else ord(DISABLED)
        self.quote_char = ord(fmt.quote) if fmt.quote is not None else ord(DISABLED)
        self.comment_start = ord(fmt.comment_marker) if fmt.comment_marker is not None else ord(DISABLED)
        self.ignore_surrounding_spaces = fmt.ignore_surrounding_spaces
        self.ignore_empty_lines = fmt.ignore_empty_lines
        self.is_last_token_delimiter = False

    def is_comment_start(self, ch):
        return ch == self.comment_start

    def is_delimiter(self, ch):
        self.is_last_token_delimiter = False
        if ch != self.delimiter[0]:
            return False
        if len(self.delimiter) == 1:
            self.is_last_token_delimiter = True
            return True
        lookahead = self.reader.look_ahead_n(len(self.delimiter) - 1)
        if len(lookahead) < len(self.delimiter) - 1:
            return False
        for i in range(len(lookahead)):
            if lookahead[i] != self.delimiter[i + 1]:
                return False
        self.reader.read_chars(len(lookahead))
        self.is_last_token_delimiter = True
        return True

    def is_escape(self, ch):
        return ch == self.escape

    def is_quote_char(self, ch):
        return ch == self.quote_char

    def is_meta_char(self, ch):
        return ch in (self.escape, self.quote_char, self.comment_start)

    def is_start_of_line(self, ch):
        return ch in (ord(LF), ord(CR), UNDEFINED)

    def is_escape_delimiter(self):
        target_len = 2 * len(self.delimiter) - 1
        lookahead = self.reader.look_ahead_n(target_len)
        if len(lookahead) < target_len:
            return False
        if lookahead[0] != self.delimiter[0]:
            return False
        for i in range(1, len(self.delimiter)):
            if lookahead[2 * i] != self.delimiter[i] or lookahead[2 * i - 1] != self.escape:
                return False
        count = self.reader.read_chars(target_len)
        return count

    def read_end_of_line(self, ch):
        if ch == ord(CR) and self.reader.look_ahead() == ord(LF):
            ch = self.reader.read()
        return ch in (ord(LF), ord(CR))

    def read_escape(self):
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

    def trim_trailing_spaces(self, content):
        length = len(content)
        while length > 0 and _is_java_whitespace(content[length - 1]):
            length -= 1
        if length != len(content):
            del content[length:]

    def next_token(self, token):
        last_char = self.reader.get_last_char()
        c = self.reader.read()
        eol = self.read_end_of_line(c)
        if self.ignore_empty_lines:
            while eol and self.is_start_of_line(last_char):
                last_char = c
                c = self.reader.read()
                eol = self.read_end_of_line(c)
                if c == END_OF_STREAM:
                    token.type = TOKEN_TYPE_EOF
                    return token

        if last_char == END_OF_STREAM or (not self.is_last_token_delimiter and c == END_OF_STREAM):
            token.type = TOKEN_TYPE_EOF
            return token

        while token.type == TOKEN_TYPE_INVALID:
            if self.ignore_surrounding_spaces:
                while c != END_OF_STREAM and _is_java_whitespace(chr(c)) and not self.is_delimiter(c) and not eol:
                    c = self.reader.read()
                    eol = self.read_end_of_line(c)

            if self.is_delimiter(c):
                token.type = TOKEN_TYPE_TOKEN
            elif eol:
                token.type = TOKEN_TYPE_EORECORD
            elif self.is_quote_char(c):
                self.parse_encapsulated_token(token)
            elif c == END_OF_STREAM:
                token.type = TOKEN_TYPE_EOF
                token.is_ready = True
            else:
                self.parse_simple_token(token, c)
        return token

    def parse_encapsulated_token(self, token):
        token.is_quoted = True
        start_line_number = self.reader.get_current_line_number()
        while True:
            c = self.reader.read()
            if self.is_escape(c):
                if self.is_escape_delimiter():
                    token.content.append(self.format.delimiter)
                else:
                    unescaped = self.read_escape()
                    if unescaped == END_OF_STREAM:
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
                            token.type = TOKEN_TYPE_TOKEN
                            return token
                        if c == END_OF_STREAM:
                            token.type = TOKEN_TYPE_EOF
                            token.is_ready = True
                            return token
                        if self.read_end_of_line(c):
                            token.type = TOKEN_TYPE_EORECORD
                            return token
                        if not _is_java_whitespace(chr(c)):
                            raise CSVParseError(
                                f"(line {self.reader.get_current_line_number()}) invalid char between encapsulated token and delimiter"
                            )
            elif c == END_OF_STREAM:
                raise CSVParseError(
                    f"(startline {start_line_number}) EOF reached before encapsulated token finished"
                )
            else:
                token.content.append(chr(c))

    def parse_simple_token(self, token, ch):
        while True:
            if self.read_end_of_line(ch):
                token.type = TOKEN_TYPE_EORECORD
                break
            if ch == END_OF_STREAM:
                token.type = TOKEN_TYPE_EOF
                token.is_ready = True
                break
            if self.is_delimiter(ch):
                token.type = TOKEN_TYPE_TOKEN
                break
            if self.is_escape(ch):
                if self.is_escape_delimiter():
                    token.content.append(self.format.delimiter)
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


def _handle_null(fmt, input_str, is_quoted):
    null_str = fmt.null_string
    strict_quote_mode = fmt.quote_mode in ('ALL_NON_NULL', 'NON_NUMERIC')
    if input_str == null_str:
        return input_str if (strict_quote_mode and is_quoted) else None
    if strict_quote_mode and null_str is None and input_str == '' and not is_quoted:
        return None
    return input_str


def parse_csv(text, config=None):
    if text is None:
        raise IllegalArgumentException("text cannot be None")
    if not isinstance(text, str):
        raise IllegalArgumentException("text must be a string")

    fmt = _Format(config)
    reader = _ExtendedBufferedReader(text)
    lexer = _Lexer(fmt, reader)
    reusable_token = _Token()

    records = []
    record_list = []

    def add_record_value(last_record):
        raw_content = "".join(reusable_token.content)
        input_val = _java_trim(raw_content) if fmt.trim else raw_content
        record_list.append(_handle_null(fmt, input_val, reusable_token.is_quoted))

    while True:
        record_list = []
        while True:
            reusable_token.reset()
            lexer.next_token(reusable_token)
            if reusable_token.type == TOKEN_TYPE_TOKEN:
                add_record_value(False)
            elif reusable_token.type == TOKEN_TYPE_EORECORD:
                add_record_value(True)
                break
            elif reusable_token.type == TOKEN_TYPE_EOF:
                if reusable_token.is_ready:
                    add_record_value(True)
                break
            elif reusable_token.type == TOKEN_TYPE_INVALID:
                raise CSVParseError(f"(line {reader.get_current_line_number()}) invalid parse sequence")
            else:
                break

        if record_list:
            records.append(record_list)
        elif reusable_token.type == TOKEN_TYPE_EOF and not reusable_token.is_ready:
            break

        if reusable_token.type == TOKEN_TYPE_EOF:
            break

    return records


def _print_with_escapes(val_str, delim_char, escape_char, out):
    pos = 0
    start = 0
    length = len(val_str)
    while pos < length:
        c = val_str[pos]
        is_delim_start = (c == delim_char)
        if c in (CR, LF) or c == escape_char or is_delim_start:
            if pos > start:
                out.append(val_str[start:pos])
            if c == LF:
                c = 'n'
            elif c == CR:
                c = 'r'
            out.append(escape_char)
            out.append(c)
            start = pos + 1
        pos += 1
    if pos > start:
        out.append(val_str[start:pos])


def _print_with_quotes(val_str, fmt, out, new_record):
    quote = False
    length = len(val_str)
    quote_char = fmt.quote
    escape_char = fmt.escape if fmt.escape is not None else quote_char
    quote_mode = fmt.quote_mode if fmt.quote_mode is not None else 'MINIMAL'

    if quote_mode in ('ALL', 'ALL_NON_NULL', 'NON_NUMERIC'):
        quote = True
    elif quote_mode == 'NONE':
        _print_with_escapes(val_str, fmt.delimiter, fmt.escape, out)
        return
    elif quote_mode == 'MINIMAL':
        if length <= 0:
            if new_record:
                quote = True
        else:
            c = val_str[0]
            if ord(c) <= ord(COMMENT):
                quote = True
            else:
                pos = 0
                while pos < length:
                    c = val_str[pos]
                    if c in (LF, CR, quote_char, escape_char, fmt.delimiter):
                        quote = True
                        break
                    pos += 1
                if not quote:
                    last_c = val_str[-1]
                    if ord(last_c) <= ord(SP):
                        quote = True

    if not quote:
        out.append(val_str)
        return

    out.append(quote_char)
    pos = 0
    start = 0
    while pos < length:
        c = val_str[pos]
        if c in (quote_char, escape_char):
            out.append(val_str[start:pos])
            out.append(escape_char)
            start = pos
        pos += 1
    out.append(val_str[start:pos])
    out.append(quote_char)


def _print_value(value, fmt, out, new_record):
    if not new_record:
        out.append(fmt.delimiter)

    if value is None:
        if fmt.null_string is None:
            char_seq = ''
        elif fmt.quote_mode == 'ALL':
            char_seq = fmt.quoted_null_string
        else:
            char_seq = fmt.null_string
        if fmt.trim:
            char_seq = _java_trim(char_seq)
        out.append(char_seq)
    else:
        if not isinstance(value, str):
            raise IllegalArgumentException("All non-null values must be strings")
        char_seq = _java_trim(value) if fmt.trim else value
        if fmt.quote is not None:
            _print_with_quotes(char_seq, fmt, out, new_record)
        elif fmt.escape is not None:
            _print_with_escapes(char_seq, fmt.delimiter, fmt.escape, out)
        else:
            out.append(char_seq)


def print_csv(records, config=None):
    if records is None:
        raise IllegalArgumentException("records cannot be None")

    fmt = _Format(config)
    out = []
    for record in records:
        if record is None:
            raise IllegalArgumentException("record cannot be None")
        new_rec = True
        for val in record:
            _print_value(val, fmt, out, new_rec)
            new_rec = False
        if fmt.record_separator is not None:
            out.append(fmt.record_separator)
    return "".join(out)
