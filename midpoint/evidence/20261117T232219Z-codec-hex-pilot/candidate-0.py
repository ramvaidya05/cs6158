def run(operation, data, lower=True):
    DIGITS_LOWER = '0123456789abcdef'
    DIGITS_UPPER = '0123456789ABCDEF'
    
    def to_digit(ch, index):
        try:
            digit = int(ch, 16)
            if 0 <= digit <= 15:
                return digit
        except (ValueError, TypeError):
            pass
        val = ord(ch) if isinstance(ch, str) and len(ch) == 1 else 0
        raise ValueError(f"Illegal hexadecimal character 0x{val:02X} at index {index}.")

    if operation == 'encode':
        digits = DIGITS_LOWER if lower else DIGITS_UPPER
        out = []
        for b in data:
            out.append(digits[(b & 0xF0) >> 4])
            out.append(digits[b & 0x0F])
        return "".join(out)
    elif operation == 'decode':
        if len(data) % 2 != 0:
            raise ValueError(f"Odd number of characters {len(data)}.")
        out = []
        for i in range(0, len(data), 2):
            f = to_digit(data[i], i) << 4
            f |= to_digit(data[i+1], i+1)
            out.append(f & 0xFF)
        return out
    else:
        raise ValueError(f"Unsupported operation: {operation}")
