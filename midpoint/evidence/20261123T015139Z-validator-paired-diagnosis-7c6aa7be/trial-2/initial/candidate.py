class CheckDigitException(Exception):
    pass


def is_blank_or_null(code: str | None) -> bool:
    if code is None:
        return True
    return len(code.strip()) == 0


POSITION_WEIGHT = [2, 1]


def to_int(character: str, left_pos: int, right_pos: int) -> int:
    if character.isdigit():
        return int(character)
    raise CheckDigitException(f"Invalid Character[{left_pos}] = '{character}'")


def weighted_value(char_value: int, left_pos: int, right_pos: int) -> int:
    weight = POSITION_WEIGHT[right_pos % 2]
    w_val = char_value * weight
    return w_val - 9 if w_val > 9 else w_val


def calculate_modulus(code: str, includes_check_digit: bool) -> int:
    total = 0
    length = len(code)
    for i in range(length):
        lth = length + (0 if includes_check_digit else 1)
        left_pos = i + 1
        right_pos = lth - i
        char_val = to_int(code[i], left_pos, right_pos)
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
