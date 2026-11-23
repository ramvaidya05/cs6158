def is_blank_or_null(code):
    if code is None:
        return True
    return len(code.strip()) == 0

def java_is_digit(ch):
    return ch.isdigit()

def java_get_numeric_value(ch):
    if '0' <= ch <= '9':
        return ord(ch) - ord('0')
    return -1

def to_int(character, left_pos, right_pos):
    if java_is_digit(character):
        num = java_get_numeric_value(character)
        if num >= 0:
            return num
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
