# Assisted finalization of the archived Gemini translation.
# Decimal blocks are pinned to the Java reference runtime, not Python Unicode data.
_DECIMAL_BASES = (48, 1632, 1776, 1984, 2406, 2534, 2662, 2790, 2918, 3046, 3174, 3302, 3430, 3558, 3664, 3792, 3872, 4160, 4240, 6112, 6160, 6470, 6608, 6784, 6800, 6992, 7088, 7232, 7248, 42528, 43216, 43264, 43472, 43504, 43600, 44016, 65296)

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
    # ASCII digits and hex letters
    if 0x30 <= cu <= 0x39:
        return cu - 0x30
    if 0x61 <= cu <= 0x66:
        return cu - 0x61 + 10
    if 0x41 <= cu <= 0x46:
        return cu - 0x41 + 10
    # Fullwidth ASCII digits and hex letters
    if 0xFF10 <= cu <= 0xFF19:
        return cu - 0xFF10
    if 0xFF41 <= cu <= 0xFF46:
        return cu - 0xFF41 + 10
    if 0xFF21 <= cu <= 0xFF26:
        return cu - 0xFF21 + 10
    for base in _DECIMAL_BASES:
        if base <= cu < base + 10:
            return cu - base
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
