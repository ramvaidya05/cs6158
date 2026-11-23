import unicodedata


class CheckDigitException(Exception):
    pass


def is_blank_or_null(code: str | None) -> bool:
    if code is None:
        return True
    trimmed = code.strip(
        "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f "
    )
    return len(trimmed) == 0


POSITION_WEIGHT = [2, 1]


def get_code_units(code: str) -> list[int]:
    encoded = code.encode("utf-16-be")
    return [encoded[i] << 8 | encoded[i + 1] for i in range(0, len(encoded), 2)]


def to_int(ch_unit: int, left_pos: int, right_pos: int) -> int:
    ch = chr(ch_unit)
    if unicodedata.category(ch) == "Nd":
        return unicodedata.digit(ch)
    raise CheckDigitException(f"Invalid Character[{left_pos}] = '{ch}'")


def weighted_value(char_value: int, left_pos: int, right_pos: int) -> int:
    weight = POSITION_WEIGHT[right_pos % 2]
    w_val = char_value * weight
    return w_val - 9 if w_val > 9 else w_val


def calculate_modulus(code_units: list[int], includes_check_digit: bool) -> int:
    total = 0
    length = len(code_units)
    for i in range(length):
        lth = length + (0 if includes_check_digit else 1)
        left_pos = i + 1
        right_pos = lth - i
        char_val = to_int(code_units[i], left_pos, right_pos)
        total += weighted_value(char_val, left_pos, right_pos)
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
        code_units = get_code_units(code)
        modulus_result = calculate_modulus(code_units, False)
        char_value = (10 - modulus_result) % 10
        return to_check_digit(char_value)
    except CheckDigitException as e:
        raise ValueError(str(e)) from e


def is_valid(code: str | None) -> bool:
    if is_blank_or_null(code):
        return False
    try:
        code_units = get_code_units(code)
        modulus_result = calculate_modulus(code_units, True)
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
