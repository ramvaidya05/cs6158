import unicodedata

DIGITS_LOWER = list("0123456789abcdef")
DIGITS_UPPER = list("0123456789ABCDEF")

def _character_digit_radix_16(ch: str) -> int:
    if len(ch) != 1:
        return -1
    code = ord(ch)
    # Basic ASCII fast path
    if 0x30 <= code <= 0x39:
        return code - 0x30
    if 0x61 <= code <= 0x66:
        return code - 0x61 + 10
    if 0x41 <= code <= 0x46:
        return code - 0x41 + 10
    
    # Fullwidth ASCII hex characters
    if 0xFF10 <= code <= 0xFF19:
        return code - 0xFF10
    if 0xFF41 <= code <= 0xFF46:
        return code - 0xFF41 + 10
    if 0xFF21 <= code <= 0xFF26:
        return code - 0xFF21 + 10

    # Unicode decimal digit fallback
    try:
        val = unicodedata.decimal(ch)
        if 0 <= val <= 9:
            return val
    except (ValueError, TypeError):
        pass
    return -1

def _to_digit(ch: str, index: int) -> int:
    digit = _character_digit_radix_16(ch)
    if digit == -1:
        raise ValueError(f"Illegal hexadecimal character {ch} at index {index}.")
    return digit

def decode_hex(data: str) -> list:
    # Java String length is in UTF-16 code units / chars
    # Python string indexing is by character
    chars = list(data)
    length = len(chars)
    if (length & 1) != 0:
        raise ValueError(f"Odd number of characters {length}.")
    
    out = []
    j = 0
    while j < length:
        f = _to_digit(chars[j], j) << 4
        j += 1
        f |= _to_digit(chars[j], j)
        j += 1
        out.append(f & 0xFF)
    return out

def encode_hex_string(data: list, to_lower: bool = True) -> str:
    digits = DIGITS_LOWER if to_lower else DIGITS_UPPER
    out = []
    for b in data:
        b_val = b & 0xFF
        out.append(digits[(0xF0 & b_val) >> 4])
        out.append(digits[0x0F & b_val])
    return "".join(out)

def run(operation: str, data, lower: bool = True):
    if operation == "encode":
        return encode_hex_string(data, to_lower=lower)
    elif operation == "decode":
        return decode_hex(data)
    else:
        raise ValueError(f"Unsupported operation: {operation}")
