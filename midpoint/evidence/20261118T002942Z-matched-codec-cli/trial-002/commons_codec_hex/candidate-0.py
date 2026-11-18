import unicodedata

DIGITS_LOWER = list("0123456789abcdef")
DIGITS_UPPER = list("0123456789ABCDEF")

def _char_digit_16(ch):
    if len(ch) != 1:
        return -1
    code = ord(ch)
    if 0x30 <= code <= 0x39:
        return code - 0x30
    if 0x61 <= code <= 0x66:
        return code - 0x61 + 10
    if 0x41 <= code <= 0x46:
        return code - 0x41 + 10
    try:
        val = unicodedata.digit(ch)
        if 0 <= val <= 9:
            return val
    except (ValueError, TypeError):
        pass
    return -1

def _to_digit(ch, index):
    digit = _char_digit_16(ch)
    if digit == -1:
        raise ValueError(f"Illegal hexadecimal character 0x{ord(ch) & 0xFF:02X} at index {index:,d}.")
    return digit

def decode_hex(data):
    if len(data) % 2 != 0:
        raise ValueError(f"Odd number of characters {len(data):,d}.")
    out = bytearray(len(data) >> 1)
    j = 0
    for i in range(len(out)):
        f = _to_digit(data[j], j) << 4
        j += 1
        f |= _to_digit(data[j], j)
        j += 1
        out[i] = f & 0xFF
    return list(out)

def encode_hex_string(data, to_lower_case=True):
    to_digits = DIGITS_LOWER if to_lower_case else DIGITS_UPPER
    out = []
    for b in data:
        out.append(to_digits[(0xF0 & b) >> 4])
        out.append(to_digits[0x0F & b])
    return "".join(out)

def run(operation, data, lower=True):
    if operation == "encode":
        return encode_hex_string(data, lower)
    elif operation == "decode":
        return decode_hex(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
