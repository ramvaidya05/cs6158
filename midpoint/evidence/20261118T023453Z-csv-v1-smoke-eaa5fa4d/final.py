import io
import numbers


class CSVParseError(Exception):
    """Raised when CSV parsing encounters an I/O or syntax error."""
    pass


class IllegalArgumentException(Exception):
    """Raised when configuration parameters or arguments are invalid or inconsistent."""
    pass


CR = '\r'
LF = '\n'
CRLF = "\r\n"
SP = ' '
TAB = '\t'
BACKSPACE = '\b'
FF = '\f'
COMMENT = '#'
END_OF_STREAM = -1
UNDEFINED = -2
DISABLED = '\ufffe'


def is_trim_char(c):
    return ord(c) <= ord(' ')


class CSVFormat:
    def __init__(self, delimiter=',', quote='"', quote_mode=None, comment_marker=None,
                 escape=None, ignore_surrounding_spaces=False, ignore_empty_lines=True,
                 record_separator="\r\n", null_string=None, trim=False, trailing_delimiter=False):
        if delimiter is None:
            raise IllegalArgumentException("Delimiter cannot be null")
        if not isinstance(delimiter, str) or len(delimiter) == 0:
            raise IllegalArgumentException("The delimiter cannot be empty")
        if '\r' in delimiter or '\n' in delimiter:
            raise IllegalArgumentException("The delimiter cannot be a line break")

        if quote is not None and len(quote) != 1:
            raise IllegalArgumentException("The quoteChar must be one character")
        if quote is not None and (quote == '\r' or quote == '\n'):
            raise IllegalArgumentException("The quoteChar cannot be a line break")
        if quote is not None and quote in delimiter:
            raise IllegalArgumentException(f"The quoteChar character and the delimiter cannot be the same ('{quote}')")

        if escape is not None and len(escape) != 1:
            raise IllegalArgumentException("The escape character must be one character")
        if escape is not None and (escape == '\r' or escape == '\n'):
            raise IllegalArgumentException("The escape character cannot be a line break")
        if escape is not None and escape in delimiter:
            raise IllegalArgumentException(f"The escape character and the delimiter cannot be the same ('{escape}')")

        if comment_marker is not None and len(comment_marker) != 1:
            raise IllegalArgumentException("The commentMarker character must be one character")
        if comment_marker is not None and (comment_marker == '\r' or comment_marker == '\n'):
            raise IllegalArgumentException("The comment start marker character cannot be a line break")
        if comment_marker is not None and comment_marker in delimiter:
            raise IllegalArgumentException(f"The comment start character and the delimiter cannot be the same ('{comment_marker}')")

        if quote is not None and quote == comment_marker:
            raise IllegalArgumentException(f"The comment start character and the quoteChar cannot be the same ('{comment_marker}')")
        if escape is not None and escape == comment_marker:
            raise IllegalArgumentException(f"The comment start and the escape character cannot be the same ('{comment_marker}')")

        if quote_mode is not None:
            valid_modes = {"ALL", "ALL_NON_NULL", "MINIMAL", "NON_NUMERIC", "NONE"}
            if quote_mode not in valid_modes:
                raise IllegalArgumentException(f"Unexpected Quote value: {quote_mode}")

        if escape is None and quote_mode == "NONE":
            raise IllegalArgumentException("No quotes mode set but no escape character is set")

        self.delimiter = delimiter
        self.quote_character = quote
        self.quote_mode = quote_mode
        self.comment_marker = comment_marker
        self.escape_character = escape
        self.ignore_surrounding_spaces = bool(ignore_surrounding_spaces)
        self.ignore_empty_lines = bool(ignore_empty_lines)
        self.record_separator = record_separator
        self.null_string = null_string
        self.trim = bool(trim)
        self.trailing_delimiter = bool(trailing_delimiter)

    def is_escape_character_set(self):
        return self.escape_character is not None

    def is_quote_character_set(self):
        return self.quote_character is not None

    def is_comment_marker_set(self):
        return self.comment_marker is not None

    def is_null_string_set(self):
        return self.null_string is not None


class ExtendedBufferedReader:
    def __init__(self, text):
        self.text = text
        self.len = len(text)
        self.pos = 0
        self.last_char = UNDEFINED
        self.eol_counter = 0
        self.closed = False

    def get_current_line_number(self):
        if self.last_char in (ord(CR), ord(LF), UNDEFINED, END_OF_STREAM):
            return self.eol_counter
        return self.eol_counter + 1

    def get_last_char(self):
        return self.last_char

    def get_position(self):
        return self.pos

    def is_closed(self):
        return self.closed

    def close(self):
        self.closed = True
        self.last_char = END_OF_STREAM

    def look_ahead(self, n=1):
        if self.pos >= self.len:
            return "" if n > 1 else END_OF_STREAM
        if n == 1:
            return ord(self.text[self.pos])
        end = min(self.pos + n, self.len)
        return self.text[self.pos:end]

    def read(self, n=1):
        if n == 1:
            if self.pos >= self.len:
                current = END_OF_STREAM
            else:
                current = ord(self.text[self.pos])
                self.pos += 1

            if (current == ord(CR) or
                (current == ord(LF) and self.last_char != ord(CR)) or
                (current == END_OF_STREAM and self.last_char != ord(CR) and self.last_char != ord(LF) and self.last_char != END_OF_STREAM)):
                self.eol_counter += 1
            self.last_char = current
            return current
        else:
            if self.pos >= self.len:
                self.last_char = END_OF_STREAM
                return ""
            end = min(self.pos + n, self.len)
            buf = self.text[self.pos:end]
            self.pos = end
            for i, ch in enumerate(buf):
                c = ord(ch)
                if c == ord(LF):
                    prev = ord(buf[i - 1]) if i > 0 else self.last_char
                    if prev != ord(CR):
                        self.eol_counter += 1
                elif c == ord(CR):
                    self.eol_counter += 1
            self.last_char = ord(buf[-1])
            return buf

    def read_line(self):
        if self.look_ahead() == END_OF_STREAM:
            return None
        buffer = []
        while True:
            current = self.read()
            if current == ord(CR):
                if self.look_ahead() == ord(LF):
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
        self.type = self.INVALID
        self.content = []
        self.is_ready = False
        self.is_quoted = False

    def reset(self):
        self.type = self.INVALID
        self.content = []
        self.is_ready = False
        self.is_quoted = False


class Lexer:
    def __init__(self, format, reader):
        self.reader = reader
        self.format = format
        self.delimiter = format.delimiter
        self.delimiter_len = len(self.delimiter)
        self.escape = ord(format.escape_character) if format.escape_character is not None else ord(DISABLED)
        self.quote_char = ord(format.quote_character) if format.quote_character is not None else ord(DISABLED)
        self.comment_start = ord(format.comment_marker) if format.comment_marker is not None else ord(DISABLED)
        self.ignore_surrounding_spaces = format.ignore_surrounding_spaces
        self.ignore_empty_lines = format.ignore_empty_lines
        self.first_eol = None
        self.is_last_token_delimiter = False

    def is_comment_start(self, ch):
        return ch == self.comment_start

    def is_delimiter(self, ch):
        self.is_last_token_delimiter = False
        if ch != ord(self.delimiter[0]):
            return False
        if self.delimiter_len == 1:
            self.is_last_token_delimiter = True
            return True
        needed = self.delimiter_len - 1
        look = self.reader.look_ahead(needed)
        if len(look) < needed or look != self.delimiter[1:]:
            return False
        self.reader.read(needed)
        self.is_last_token_delimiter = True
        return True

    def is_end_of_file(self, ch):
        return ch == END_OF_STREAM

    def is_escape(self, ch):
        return ch == self.escape

    def is_escape_delimiter(self):
        target = []
        for i, c in enumerate(self.delimiter):
            if i > 0:
                target.append(chr(self.escape))
            target.append(c)
        needed = len(target)
        look = self.reader.look_ahead(needed)
        if len(look) == needed and look == "".join(target):
            self.reader.read(needed)
            return True
        return False

    def is_meta_char(self, ch):
        return ch in (self.escape, self.quote_char, self.comment_start)

    def is_quote_char(self, ch):
        return ch == self.quote_char

    def is_start_of_line(self, ch):
        return ch in (ord(LF), ord(CR), UNDEFINED)

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
        if ch == ord('n'):
            return ord(LF)
        if ch == ord('t'):
            return ord(TAB)
        if ch == ord('b'):
            return ord(BACKSPACE)
        if ch == ord('f'):
            return ord(FF)
        if ch in (ord(CR), ord(LF), ord(FF), ord(TAB), ord(BACKSPACE)):
            return ch
        if ch == END_OF_STREAM:
            raise CSVParseError("EOF whilst processing escape sequence")
        if self.is_meta_char(ch):
            return ch
        return END_OF_STREAM

    def trim_trailing_spaces(self, content):
        while content and chr(content[-1]).isspace():
            content.pop()

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

        if self.is_start_of_line(last_char) and self.is_comment_start(c):
            line = self.reader.read_line()
            if line is None:
                token.type = Token.EOF
                return token
            token.content.extend([ord(x) for x in line.strip()])
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

    def parse_encapsulated_token(self, token):
        token.is_quoted = True
        start_line_number = self.reader.get_current_line_number()
        while True:
            c = self.reader.read()
            if self.is_escape(c):
                if self.is_escape_delimiter():
                    token.content.extend([ord(x) for x in self.delimiter])
                else:
                    unescaped = self.read_escape()
                    if unescaped == END_OF_STREAM:
                        token.content.append(c)
                        token.content.append(self.reader.get_last_char())
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
                            raise CSVParseError(f"(line {self.reader.get_current_line_number()}) invalid char between encapsulated token and delimiter")
            elif self.is_end_of_file(c):
                raise CSVParseError(f"(startline {start_line_number}) EOF reached before encapsulated token finished")
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
            if self.is_escape(ch):
                if self.is_escape_delimiter():
                    token.content.extend([ord(x) for x in self.delimiter])
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


def _build_format(config):
    if config is None:
        config = {}
    delimiter = config.get("delimiter", ",")
    quote = config.get("quote", '"')
    escape = config.get("escape", None)
    record_separator = config.get("record_separator", "\r\n")
    null_string = config.get("null_string", None)
    quote_mode = config.get("quote_mode", None)
    ignore_empty_lines = config.get("ignore_empty_lines", True)
    ignore_surrounding_spaces = config.get("ignore_surrounding_spaces", False)
    trim = config.get("trim", False)
    trailing_delimiter = config.get("trailing_delimiter", False)

    return CSVFormat(
        delimiter=delimiter,
        quote=quote,
        quote_mode=quote_mode,
        escape=escape,
        ignore_surrounding_spaces=ignore_surrounding_spaces,
        ignore_empty_lines=ignore_empty_lines,
        record_separator=record_separator,
        null_string=null_string,
        trim=trim,
        trailing_delimiter=trailing_delimiter
    )


def parse_csv(text, config=None):
    format = _build_format(config)
    reader = ExtendedBufferedReader(text)
    lexer = Lexer(format, reader)
    reusable_token = Token()
    record_list = []
    records = []

    strict_quote_mode = format.quote_mode in ("ALL_NON_NULL", "NON_NUMERIC")

    def handle_null(input_val, is_quoted):
        if input_val == format.null_string:
            return input_val if (strict_quote_mode and is_quoted) else None
        if strict_quote_mode and format.null_string is None and input_val == "" and not is_quoted:
            return None
        return input_val

    def add_record_value(last_record):
        raw_str = "".join(chr(x) for x in reusable_token.content)
        val = raw_str.strip() if format.trim else raw_str
        if last_record and val == "" and format.trailing_delimiter:
            return
        record_list.append(handle_null(val, reusable_token.is_quoted))

    while True:
        record_list.clear()
        while True:
            reusable_token.reset()
            lexer.next_token(reusable_token)
            if reusable_token.type == Token.TOKEN:
                add_record_value(False)
            elif reusable_token.type == Token.EORECORD:
                add_record_value(True)
                break
            elif reusable_token.type == Token.EOF:
                if reusable_token.is_ready:
                    add_record_value(True)
                break
            elif reusable_token.type == Token.INVALID:
                raise CSVParseError(f"(line {reader.get_current_line_number()}) invalid parse sequence")
            elif reusable_token.type == Token.COMMENT:
                reusable_token.type = Token.TOKEN
            else:
                raise CSVParseError(f"Unexpected Token type: {reusable_token.type}")

        if record_list:
            records.append(list(record_list))
        elif reusable_token.type == Token.EOF:
            break

        if reusable_token.type == Token.EOF:
            break

    return records


def _is_delimiter(ch, char_seq, pos, delim):
    if ch != delim[0]:
        return False
    delim_len = len(delim)
    if pos + delim_len > len(char_seq):
        return False
    return char_seq[pos:pos + delim_len] == delim


def _print_with_escapes(char_seq, out, delimiter, escape):
    pos = 0
    start = 0
    end = len(char_seq)
    delim_len = len(delimiter)

    while pos < end:
        c = char_seq[pos]
        is_delim_start = _is_delimiter(c, char_seq, pos, delimiter)
        if c in (CR, LF, escape) or is_delim_start:
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


def _print_with_quotes(orig_val, char_seq, out, new_record, format):
    quote = False
    pos = 0
    length = len(char_seq)
    quote_char = format.quote_character
    escape_char = format.escape_character if format.is_escape_character_set() else quote_char
    quote_mode = format.quote_mode if format.quote_mode is not None else "MINIMAL"

    if quote_mode in ("ALL", "ALL_NON_NULL"):
        quote = True
    elif quote_mode == "NON_NUMERIC":
        quote = not isinstance(orig_val, numbers.Number)
    elif quote_mode == "NONE":
        _print_with_escapes(char_seq, out, format.delimiter, format.escape_character)
        return
    elif quote_mode == "MINIMAL":
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
                    if (c in (LF, CR, quote_char, escape_char) or
                            _is_delimiter(c, char_seq, pos, format.delimiter)):
                        quote = True
                        break
                    pos += 1
                if not quote:
                    last_c = char_seq[-1]
                    if is_trim_char(last_c):
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
    start = 0
    while pos < length:
        c = char_seq[pos]
        if c == quote_char or c == escape_char:
            out.write(char_seq[start:pos])
            out.write(escape_char)
            start = pos
        pos += 1
    out.write(char_seq[start:pos])
    out.write(quote_char)


def print_csv(records, config=None):
    format = _build_format(config)
    out = io.StringIO()

    for record in records:
        new_record = True
        for val in record:
            if val is None:
                if format.null_string is None:
                    char_seq = ""
                elif format.quote_mode == "ALL":
                    q = format.quote_character if format.quote_character is not None else ""
                    char_seq = f"{q}{format.null_string}{q}"
                else:
                    char_seq = format.null_string
            else:
                char_seq = str(val)

            if format.trim:
                char_seq = char_seq.strip()

            if not new_record:
                out.write(format.delimiter)

            if val is None:
                out.write(char_seq)
            elif format.is_quote_character_set():
                _print_with_quotes(val, char_seq, out, new_record, format)
            elif format.is_escape_character_set():
                _print_with_escapes(char_seq, out, format.delimiter, format.escape_character)
            else:
                out.write(char_seq)

            new_record = False

        if format.trailing_delimiter:
            out.write(format.delimiter)
        if format.record_separator is not None:
            out.write(format.record_separator)

    return out.getvalue()
