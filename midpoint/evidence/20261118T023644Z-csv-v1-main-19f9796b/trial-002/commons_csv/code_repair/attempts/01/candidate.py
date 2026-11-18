import numbers

class CSVParseError(Exception):
    pass

class IllegalArgumentException(Exception):
    pass

CR = '\r'
LF = '\n'
CRLF = '\r\n'
SP = ' '
COMMENT_CHAR = '#'
DISABLED = '\ufffe'
EOF_CHAR = -1
UNDEFINED = -2

def _is_line_break(ch):
    return ch in (CR, LF)

def _is_trim_char(ch):
    return ord(ch) <= ord(SP)

class _ExtendedReader:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)
        self.last_char = UNDEFINED
        self.eol_counter = 0
        self.position = 0
        self.closed = False

    def close(self):
        self.closed = True
        self.last_char = EOF_CHAR

    def is_closed(self):
        return self.closed

    def get_position(self):
        return self.position

    def get_current_line_number(self):
        if self.last_char in (ord(CR), ord(LF), UNDEFINED, EOF_CHAR):
            return self.eol_counter
        return self.eol_counter + 1

    def get_last_char(self):
        return self.last_char

    def look_ahead(self, n=1):
        if self.pos >= self.length:
            return EOF_CHAR if n == 1 else []
        if n == 1:
            return ord(self.text[self.pos])
        end = min(self.pos + n, self.length)
        return [ord(c) for c in self.text[self.pos:end]]

    def read(self):
        if self.pos >= self.length:
            current = EOF_CHAR
        else:
            current = ord(self.text[self.pos])
            self.pos += 1

        if current == ord(CR) or (current == ord(LF) and self.last_char != ord(CR)) or \
           (current == EOF_CHAR and self.last_char != ord(CR) and self.last_char != ord(LF) and self.last_char != EOF_CHAR):
            self.eol_counter += 1

        self.last_char = current
        if current != EOF_CHAR:
            self.position += 1
        return self.last_char

    def read_line(self):
        if self.look_ahead() == EOF_CHAR:
            return None
        buf = []
        while True:
            current = self.read()
            if current == ord(CR):
                nxt = self.look_ahead()
                if nxt == ord(LF):
                    self.read()
            if current in (EOF_CHAR, ord(LF), ord(CR)):
                break
            buf.append(chr(current))
        return "".join(buf)

class _Token:
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
        self.content.clear()
        self.is_ready = False
        self.is_quoted = False

    def get_content_str(self):
        return "".join(chr(c) for c in self.content)

class _Lexer:
    def __init__(self, fmt, reader):
        self.reader = reader
        self.delimiter = fmt['delimiter']
        self.delimiter_chars = [ord(c) for c in self.delimiter]
        self.escape = ord(fmt['escape']) if fmt['escape'] is not None else ord(DISABLED)
        self.quote_char = ord(fmt['quote']) if fmt['quote'] is not None else ord(DISABLED)
        self.comment_start = ord(fmt['comment_marker']) if fmt.get('comment_marker') is not None else ord(DISABLED)
        self.ignore_surrounding_spaces = fmt['ignore_surrounding_spaces']
        self.ignore_empty_lines = fmt['ignore_empty_lines']
        self.first_eol = None
        self.is_last_token_delimiter = False

    def close(self):
        self.reader.close()

    def is_closed(self):
        return self.reader.is_closed()

    def get_character_position(self):
        return self.reader.get_position()

    def get_current_line_number(self):
        return self.reader.get_current_line_number()

    def is_comment_start(self, ch):
        return ch == self.comment_start

    def is_delimiter(self, ch):
        self.is_last_token_delimiter = False
        if ch != self.delimiter_chars[0]:
            return False
        delim_len = len(self.delimiter_chars)
        if delim_len == 1:
            self.is_last_token_delimiter = True
            return True
        ahead = self.reader.look_ahead(delim_len - 1)
        if len(ahead) < delim_len - 1:
            return False
        for i in range(delim_len - 1):
            if ahead[i] != self.delimiter_chars[i + 1]:
                return False
        for _ in range(delim_len - 1):
            self.reader.read()
        self.is_last_token_delimiter = True
        return True

    def is_end_of_file(self, ch):
        return ch == EOF_CHAR

    def is_escape(self, ch):
        return ch == self.escape

    def is_quote_char(self, ch):
        return ch == self.quote_char

    def is_start_of_line(self, ch):
        return ch in (ord(LF), ord(CR), UNDEFINED)

    def is_escape_delimiter(self):
        delim_len = len(self.delimiter_chars)
        if delim_len <= 1:
            return False
        target_len = 2 * delim_len - 1
        ahead = self.reader.look_ahead(target_len)
        if len(ahead) < target_len:
            return False
        if ahead[0] != self.delimiter_chars[0]:
            return False
        for i in range(1, delim_len):
            if ahead[2 * i] != self.delimiter_chars[i] or ahead[2 * i - 1] != self.escape:
                return False
        for _ in range(target_len):
            self.reader.read()
        return True

    def is_meta_char(self, ch):
        return ch in (self.escape, self.quote_char, self.comment_start)

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
        elif ch == EOF_CHAR:
            raise CSVParseError("EOF whilst processing escape sequence")
        else:
            if self.is_meta_char(ch):
                return ch
            return EOF_CHAR

    def trim_trailing_spaces(self, buf):
        while buf and chr(buf[-1]).isspace():
            buf.pop()

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
                    token.type = _Token.EOF
                    return token

        if self.is_end_of_file(last_char) or (not self.is_last_token_delimiter and self.is_end_of_file(c)):
            token.type = _Token.EOF
            return token

        if self.is_start_of_line(last_char) and self.is_comment_start(c):
            line = self.reader.read_line()
            if line is None:
                token.type = _Token.EOF
                return token
            comment = line.strip()
            token.content.extend(ord(x) for x in comment)
            token.type = _Token.COMMENT
            return token

        while token.type == _Token.INVALID:
            if self.ignore_surrounding_spaces:
                while c != EOF_CHAR and chr(c).isspace() and not self.is_delimiter(c) and not eol:
                    c = self.reader.read()
                    eol = self.read_end_of_line(c)

            if self.is_delimiter(c):
                token.type = _Token.TOKEN
            elif eol:
                token.type = _Token.EORECORD
            elif self.is_quote_char(c):
                self.parse_encapsulated_token(token)
            elif self.is_end_of_file(c):
                token.type = _Token.EOF
                token.is_ready = True
            else:
                self.parse_simple_token(token, c)
        return token

    def parse_encapsulated_token(self, token):
        token.is_quoted = True
        start_line_number = self.get_current_line_number()
        while True:
            c = self.reader.read()
            if self.is_escape(c):
                if self.is_escape_delimiter():
                    token.content.extend(self.delimiter_chars)
                else:
                    unescaped = self.read_escape()
                    if unescaped == EOF_CHAR:
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
                            token.type = _Token.TOKEN
                            return token
                        if self.is_end_of_file(c):
                            token.type = _Token.EOF
                            token.is_ready = True
                            return token
                        if self.read_end_of_line(c):
                            token.type = _Token.EORECORD
                            return token
                        if c == EOF_CHAR or not chr(c).isspace():
                            raise CSVParseError(f"(line {self.get_current_line_number()}) invalid char between encapsulated token and delimiter")
            elif self.is_end_of_file(c):
                raise CSVParseError(f"(startline {start_line_number}) EOF reached before encapsulated token finished")
            else:
                token.content.append(c)

    def parse_simple_token(self, token, ch):
        while True:
            if self.read_end_of_line(ch):
                token.type = _Token.EORECORD
                break
            if self.is_end_of_file(ch):
                token.type = _Token.EOF
                token.is_ready = True
                break
            if self.is_delimiter(ch):
                token.type = _Token.TOKEN
                break
            if self.is_escape(ch):
                if self.is_escape_delimiter():
                    token.content.extend(self.delimiter_chars)
                else:
                    unescaped = self.read_escape()
                    if unescaped == EOF_CHAR:
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
    fmt = {
        'delimiter': ',',
        'quote': '"',
        'escape': None,
        'record_separator': CRLF,
        'null_string': None,
        'quote_mode': 'MINIMAL',
        'ignore_empty_lines': True,
        'ignore_surrounding_spaces': False,
        'trim': False,
        'trailing_delimiter': False,
        'comment_marker': None,
    }
    if config:
        for k, v in config.items():
            if k in fmt:
                fmt[k] = v
            else:
                raise IllegalArgumentException(f"Unknown config key: {k}")

    delim = fmt['delimiter']
    if not delim:
        raise IllegalArgumentException("The delimiter cannot be empty")
    if any(c in delim for c in (CR, LF)):
        raise IllegalArgumentException("The delimiter cannot be a line break")

    quote_char = fmt['quote']
    if quote_char is not None:
        if len(quote_char) != 1:
            raise IllegalArgumentException("Quote must be a single character")
        if _is_line_break(quote_char):
            raise IllegalArgumentException("The quoteChar cannot be a line break")
        if quote_char in delim:
            raise IllegalArgumentException("The quoteChar character and the delimiter cannot be the same")

    escape_char = fmt['escape']
    if escape_char is not None:
        if len(escape_char) != 1:
            raise IllegalArgumentException("Escape must be a single character")
        if _is_line_break(escape_char):
            raise IllegalArgumentException("The escape character cannot be a line break")
        if escape_char in delim:
            raise IllegalArgumentException("The escape character and the delimiter cannot be the same")

    comment_marker = fmt['comment_marker']
    if comment_marker is not None:
        if len(comment_marker) != 1:
            raise IllegalArgumentException("Comment marker must be a single character")
        if _is_line_break(comment_marker):
            raise IllegalArgumentException("The comment start marker character cannot be a line break")
        if comment_marker in delim:
            raise IllegalArgumentException("The comment start character and the delimiter cannot be the same")
        if quote_char is not None and quote_char == comment_marker:
            raise IllegalArgumentException("The comment start character and the quoteChar cannot be the same")
        if escape_char is not None and escape_char == comment_marker:
            raise IllegalArgumentException("The comment start and the escape character cannot be the same")

    quote_mode = fmt['quote_mode']
    valid_modes = ('ALL', 'ALL_NON_NULL', 'MINIMAL', 'NON_NUMERIC', 'NONE')
    if quote_mode not in valid_modes:
        raise IllegalArgumentException(f"Invalid quote mode: {quote_mode}")

    if escape_char is None and quote_mode == 'NONE':
        raise IllegalArgumentException("No quotes mode set but no escape character is set")

    return fmt

def parse_csv(text, config=None):
    fmt = _build_format(config)
    reader = _ExtendedReader(text)
    lexer = _Lexer(fmt, reader)
    reusable_token = _Token()
    records = []

    null_string = fmt['null_string']
    strict_quote_mode = fmt['quote_mode'] in ('ALL_NON_NULL', 'NON_NUMERIC')
    trim_flag = fmt['trim']
    trailing_delim = fmt['trailing_delimiter']

    def handle_null(input_str, is_quoted):
        if input_str == null_string:
            return input_str if (strict_quote_mode and is_quoted) else None
        if strict_quote_mode and null_string is None and input_str == "" and not is_quoted:
            return None
        return input_str

    def add_record_value(record_list, last_record):
        raw_content = reusable_token.get_content_str()
        input_val = raw_content.strip() if trim_flag else raw_content
        if last_record and input_val == "" and trailing_delim:
            return
        record_list.append(handle_null(input_val, reusable_token.is_quoted))

    while True:
        record_list = []
        while True:
            reusable_token.reset()
            lexer.next_token(reusable_token)
            if reusable_token.type == _Token.TOKEN:
                add_record_value(record_list, False)
            elif reusable_token.type == _Token.EORECORD:
                add_record_value(record_list, True)
                break
            elif reusable_token.type == _Token.EOF:
                if reusable_token.is_ready:
                    add_record_value(record_list, True)
                break
            elif reusable_token.type == _Token.INVALID:
                raise CSVParseError(f"(line {lexer.get_current_line_number()}) invalid parse sequence")
            elif reusable_token.type == _Token.COMMENT:
                reusable_token.type = _Token.TOKEN
            else:
                raise CSVParseError(f"Unexpected token type: {reusable_token.type}")

        if record_list:
            records.append(record_list)
        elif reusable_token.type == _Token.EORECORD and not fmt['ignore_empty_lines']:
            records.append([""])
        elif reusable_token.type == _Token.EOF and not reusable_token.is_ready:
            break

        if reusable_token.type == _Token.EOF:
            break

    return records

def _print_with_escapes(char_seq, delim, escape, out):
    delim_len = len(delim)
    start = 0
    pos = 0
    length = len(char_seq)
    while pos < length:
        c = char_seq[pos]
        is_delim_start = char_seq.startswith(delim, pos)
        if c == CR or c == LF or c == escape or is_delim_start:
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

def _print_with_quotes(obj, char_seq, fmt, new_record, out):
    quote = False
    length = len(char_seq)
    delim = fmt['delimiter']
    quote_char = fmt['quote']
    escape_char = fmt['escape'] if fmt['escape'] is not None else quote_char
    quote_mode = fmt['quote_mode']

    pos = 0
    start = 0

    if quote_mode in ('ALL', 'ALL_NON_NULL'):
        quote = True
    elif quote_mode == 'NON_NUMERIC':
        quote = not isinstance(obj, (numbers.Number, int, float)) or isinstance(obj, bool)
    elif quote_mode == 'NONE':
        _print_with_escapes(char_seq, delim, fmt['escape'], out)
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
                    if c in (LF, CR, quote_char, escape_char) or char_seq.startswith(delim, pos):
                        quote = True
                        break
                    pos += 1
                if not quote:
                    last_c = char_seq[-1]
                    if _is_trim_char(last_c):
                        quote = True
        if not quote:
            out.append(char_seq)
            return
    else:
        raise IllegalArgumentException(f"Unexpected Quote value: {quote_mode}")

    if not quote:
        out.append(char_seq)
        return

    out.append(quote_char)
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

def print_csv(records, config=None):
    fmt = _build_format(config)
    out = []

    null_string = fmt['null_string']
    quoted_null_string = (fmt['quote'] + null_string + fmt['quote']) if (fmt['quote'] is not None and null_string is not None) else None
    trim_flag = fmt['trim']
    quote_mode = fmt['quote_mode']
    has_quote = fmt['quote'] is not None
    has_escape = fmt['escape'] is not None
    delim = fmt['delimiter']
    record_sep = fmt['record_separator']
    trailing_delim = fmt['trailing_delimiter']

    for record in records:
        new_record = True
        for val in record:
            if val is None:
                if null_string is None:
                    char_seq = ""
                elif quote_mode == 'ALL':
                    char_seq = quoted_null_string
                else:
                    char_seq = null_string
            elif isinstance(val, str):
                char_seq = val
            else:
                char_seq = str(val)

            if trim_flag:
                char_seq = char_seq.strip()

            if not new_record:
                out.append(delim)

            if val is None:
                out.append(char_seq)
            elif has_quote:
                _print_with_quotes(val, char_seq, fmt, new_record, out)
            elif has_escape:
                _print_with_escapes(char_seq, delim, fmt['escape'], out)
            else:
                out.append(char_seq)

            new_record = False

        if trailing_delim:
            out.append(delim)
        if record_sep is not None:
            out.append(record_sep)

    return "".join(out)
