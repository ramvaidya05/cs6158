import unicodedata

DIGITS_LOWER = list("0123456789abcdef")
DIGITS_UPPER = list("0123456789ABCDEF")

def _to_code_units(s: str) -> list:
    units = []
    for ch in s:
        cp = ord(ch)
        if cp <= 0xFFFF:
            units.append(cp)
        else:
            cp -= 0x10000
            units.append(0xD800 + (cp >> 10))
            units.append(0xDC00 + (cp & 0x3FF))
    return units

def _character_digit_radix_16(cu: int) -> int:
    if 0x30 <= cu <= 0x39:
        return cu - 0x30
    if 0x61 <= cu <= 0x66:
        return cu - 0x61 + 10
    if 0x41 <= cu <= 0x46:
        return cu - 0x41 + 10
    if 0xFF10 <= cu <= 0xFF19:
        return cu - 0xFF10
    if 0xFF41 <= cu <= 0xFF46:
        return cu - 0xFF41 + 10
    if 0xFF21 <= cu <= 0xFF26:
        return cu - 0xFF21 + 10
    try:
        v = unicodedata.decimal(chr(cu), -1)
        if 0 <= v <= 9:
            return v
    except Exception:
        pass
    return -1

def _to_digit(cu: int, index: int) -> int:
    digit = _character_digit_radix_16(cu)
    if digit == -1:
        raise ValueError(f"Illegal hexadecimal character {chr(cu)!r} at index {index}.")
    return digit

def decode_hex(data: str) -> list:
    code_units = _to_code_units(data)
    length = len(code_units)
    if (length & 1) != 0:
        raise ValueError(f"Odd number of characters {length}.")
    
    out = []
    j = 0
    while j < length:
        f = _to_digit(code_units[j], j) << 4
        j += 1
        f |= _to_digit(code_units[j], j)
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
