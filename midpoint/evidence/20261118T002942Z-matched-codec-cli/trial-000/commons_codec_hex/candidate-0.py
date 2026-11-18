import unicodedata

DIGITS_LOWER = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
DIGITS_UPPER = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']

def _character_digit(ch: str, radix: int = 16) -> int:
    if len(ch) != 1:
        return -1
    code = ord(ch)
    if 0x30 <= code <= 0x39:  # '0'-'9'
        val = code - 0x30
    elif 0x61 <= code <= 0x7A:  # 'a'-'z'
        val = code - 0x61 + 10
    elif 0x41 <= code <= 0x5A:  # 'A'-'Z'
        val = code - 0x41 + 10
    elif 0xFF10 <= code <= 0xFF19:  # Fullwidth '0'-'9'
        val = code - 0xFF10
    elif 0xFF41 <= code <= 0xFF5A:  # Fullwidth 'a'-'z'
        val = code - 0xFF41 + 10
    elif 0xFF21 <= code <= 0xFF3A:  # Fullwidth 'A'-'Z'
        val = code - 0xFF21 + 10
    else:
        try:
            val = unicodedata.digit(ch)
        except (ValueError, TypeError):
            return -1
    return val if val < radix else -1

def to_digit(ch: str, index: int) -> int:
    digit = _character_digit(ch, 16)
    if digit == -1:
        code_val = ord(ch) & 0xFF if len(ch) == 1 else 0
        raise ValueError(f"Illegal hexadecimal character {ch} at index {index}")
    return digit

def encode_hex(data: list, to_lower_case: bool = True) -> str:
    digits = DIGITS_LOWER if to_lower_case else DIGITS_UPPER
    out = []
    for byte in data:
        byte = byte & 0xFF
        out.append(digits[(0xF0 & byte) >> 4])
        out.append(digits[0x0F & byte])
    return "".join(out)

def decode_hex(data: str) -> list:
    if (len(data) & 1) != 0:
        raise ValueError(f"Odd number of characters {len(data)}.")
    out = []
    j = 0
    while j < len(data):
        f = to_digit(data[j], j) << 4
        j += 1
        f |= to_digit(data[j], j)
        j += 1
        out.append(f & 0xFF)
    return out

def run(operation: str, data, lower: bool = True):
    if operation == "encode":
        return encode_hex(data, lower)
    elif operation == "decode":
        return decode_hex(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
