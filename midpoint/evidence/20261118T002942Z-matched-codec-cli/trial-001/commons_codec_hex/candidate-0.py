import unicodedata

DIGITS_LOWER = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
DIGITS_UPPER = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']

def _char_digit(ch: str, radix: int = 16) -> int:
    if len(ch) != 1:
        return -1
    if '0' <= ch <= '9':
        val = ord(ch) - ord('0')
    elif 'a' <= ch <= 'z':
        val = ord(ch) - ord('a') + 10
    elif 'A' <= ch <= 'Z':
        val = ord(ch) - ord('A') + 10
    else:
        try:
            val = unicodedata.digit(ch)
        except (ValueError, TypeError):
            return -1
    return val if val < radix else -1

def _to_digit(ch: str, index: int) -> int:
    digit = _char_digit(ch, 16)
    if digit == -1:
        raise ValueError(f"Illegal hexadecimal character 0x{ord(ch) & 0xFF:02X} at index {index:d}.")
    return digit

def decode_hex(data: str) -> list:
    data_chars = list(data)
    length = len(data_chars)
    if (length & 1) != 0:
        raise ValueError(f"Odd number of characters {length:d}.")
    out = []
    j = 0
    while j < length:
        f = _to_digit(data_chars[j], j) << 4
        j += 1
        f |= _to_digit(data_chars[j], j)
        j += 1
        out.append(f & 0xFF)
    return out

def encode_hex_string(data: list, lower: bool = True) -> str:
    to_digits = DIGITS_LOWER if lower else DIGITS_UPPER
    out = []
    for b in data:
        b = b & 0xFF
        out.append(to_digits[(0xF0 & b) >> 4])
        out.append(to_digits[0x0F & b])
    return "".join(out)

def run(operation: str, data, lower: bool = True):
    if operation == "encode":
        return encode_hex_string(data, lower)
    elif operation == "decode":
        return decode_hex(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
