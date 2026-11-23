JAVA_DECIMAL_BASES = [
    48, 1632, 1776, 1984, 2406, 2534, 2662, 2790, 2918, 3046, 3174, 3302, 3430, 3558, 3664, 3792,
    3872, 4160, 4240, 6112, 6160, 6470, 6608, 6784, 6800, 6992, 7088, 7232, 7248, 42528, 43216,
    43264, 43472, 43504, 43600, 44016, 65296
]

def get_numeric_value(ch):
    cp = ord(ch)
    for base in JAVA_DECIMAL_BASES:
        if base <= cp < base + 10:
            return cp - base
    return -1

def is_blank_or_null(code):
    if code is None:
        return True
    return len(code.strip()) == 0

def to_int(character, left_pos, right_pos):
    val = get_numeric_value(character)
    if val >= 0:
        return val
    raise ValueError(f"Invalid Character[{left_pos}] = '{character}'")

def weighted_value(char_value, left_pos, right_pos):
    position_weight = [2, 1]
    weight = position_weight[right_pos % 2]
    w_val = char_value * weight
    return w_val - 9 if w_val > 9 else w_val

def calculate_modulus(code, includes_check_digit):
    modulus = 10
    total = 0
    for i, ch in enumerate(code):
        lth = len(code) + (0 if includes_check_digit else 1)
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
    modulus = 10
    modulus_result = calculate_modulus(code, False)
    char_value = (modulus - modulus_result) % modulus
    return to_check_digit(char_value)

def is_valid(code):
    if is_blank_or_null(code):
        return False
    try:
        modulus_result = calculate_modulus(code, True)
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
