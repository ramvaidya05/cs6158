import struct

class CheckDigitException(Exception):
    pass

JAVA_DECIMAL_BASES = (
    48, 1632, 1776, 1984, 2406, 2534, 2662, 2790, 2918, 3046, 3174, 3302, 3430, 3558, 3664, 3792, 3872,
    4160, 4240, 6112, 6160, 6470, 6608, 6784, 6800, 6992, 7088, 7232, 7248, 42528, 43216, 43264, 43472,
    43504, 43600, 44016, 65296
)
POSITION_WEIGHT = (2, 1)

def to_utf16_units(code: str) -> list[int]:
    raw = code.encode('utf-16-le', errors='surrogatepass')
    return list(struct.unpack(f'<{len(raw)//2}H', raw))

def is_blank_or_null(code: str | None) -> bool:
    if code is None:
        return True
    units = to_utf16_units(code)
    start = 0
    end = len(units)
    while start < end and units[start] <= 32:
        start += 1
    while end > start and units[end - 1] <= 32:
        end -= 1
    return (end - start) == 0

def get_java_digit_value(unit: int) -> int:
    for b in JAVA_DECIMAL_BASES:
        if b <= unit <= b + 9:
            return unit - b
    return -1

def to_int(unit: int, left_pos: int) -> int:
    digit_val = get_java_digit_value(unit)
    if digit_val != -1:
        return digit_val
    char_str = chr(unit)
    raise CheckDigitException(f"Invalid Character[{left_pos}] = '{char_str}'")

def weighted_value(char_value: int, right_pos: int) -> int:
    weight = POSITION_WEIGHT[right_pos % 2]
    w_val = char_value * weight
    return w_val - 9 if w_val > 9 else w_val

def calculate_modulus(code: str, includes_check_digit: bool) -> int:
    units = to_utf16_units(code)
    length = len(units)
    total = 0
    for i in range(length):
        lth = length + (0 if includes_check_digit else 1)
        left_pos = i + 1
        right_pos = lth - i
        char_val = to_int(units[i], left_pos)
        total += weighted_value(char_val, right_pos)
    if total == 0:
        raise CheckDigitException("Invalid code, sum is zero")
    return total % 10

def to_check_digit(char_value: int) -> str:
    if 0 <= char_value <= 9:
        return str(char_value)
    raise CheckDigitException(f"Invalid Check Digit Value ={char_value}")

def calculate(code: str | None) -> str:
    if is_blank_or_null(code):
        raise ValueError("Code is missing")
    try:
        modulus_result = calculate_modulus(code, False)
        char_value = (10 - modulus_result) % 10
        return to_check_digit(char_value)
    except CheckDigitException as e:
        raise ValueError(str(e)) from e

def is_valid(code: str | None) -> bool:
    if is_blank_or_null(code):
        return False
    try:
        modulus_result = calculate_modulus(code, True)
        return modulus_result == 0
    except CheckDigitException:
        return False

def run(operation: str, data: str | None):
    if operation == "calculate":
        return calculate(data)
    elif operation == "isValid":
        return is_valid(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
