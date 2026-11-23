import unicodedata

def is_blank_or_null(code):
    if code is None:
        return True
    trimmed = code.strip(''.join(chr(i) for i in range(33)))
    return len(trimmed) == 0

def to_utf16_units(code):
    raw = code.encode('utf-16-le')
    return [chr(raw[i] | (raw[i+1] << 8)) for i in range(0, len(raw), 2)]

def to_int(character, left_pos, right_pos):
    if unicodedata.category(character) == 'Nd':
        return unicodedata.decimal(character)
    raise ValueError(f"Invalid Character[{left_pos}] = '{character}'")

def weighted_value(char_value, left_pos, right_pos):
    position_weight = [2, 1]
    weight = position_weight[right_pos % 2]
    w_val = char_value * weight
    return w_val - 9 if w_val > 9 else w_val

def calculate_modulus(code_units, includes_check_digit):
    modulus = 10
    total = 0
    length = len(code_units)
    for i, ch in enumerate(code_units):
        lth = length + (0 if includes_check_digit else 1)
        left_pos = i + 1
        right_pos = lth - i
        char_val = to_int(ch, left_pos, right_pos)
        total += weighted_value(char_val, left_pos, right_pos)
    if total == 0:
        raise ValueError("Invalid code, sum is zero")
    return total % modulus

def to_check_digit(char_value):
    if 0 <= char_value <= 9:
        return str(char_value)
    raise ValueError(f"Invalid Check Digit Value ={char_value}")

def calculate(code):
    if is_blank_or_null(code):
        raise ValueError("Code is missing")
    units = to_utf16_units(code)
    modulus = 10
    modulus_result = calculate_modulus(units, False)
    char_value = (modulus - modulus_result) % modulus
    return to_check_digit(char_value)

def is_valid(code):
    if is_blank_or_null(code):
        return False
    try:
        units = to_utf16_units(code)
        modulus_result = calculate_modulus(units, True)
        return modulus_result == 0
    except ValueError:
        return False

def run(operation, data):
    if operation == "calculate":
        return calculate(data)
    elif operation == "isValid":
        return is_valid(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
