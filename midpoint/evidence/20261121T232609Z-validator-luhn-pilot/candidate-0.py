def _is_blank_or_null(code: str | None) -> bool:
    if code is None:
        return True
    return len(code.strip()) == 0


def _is_digit(ch: str) -> bool:
    return '0' <= ch <= '9'


def _get_numeric_value(ch: str) -> int:
    return ord(ch) - ord('0')


class LuhnCheckDigit:
    MODULUS = 10
    POSITION_WEIGHT = [2, 1]

    def weighted_value(self, char_value: int, left_pos: int, right_pos: int) -> int:
        weight = self.POSITION_WEIGHT[right_pos % 2]
        weighted = char_value * weight
        return weighted - 9 if weighted > 9 else weighted

    def to_int(self, character: str, left_pos: int, right_pos: int) -> int:
        if _is_digit(character):
            return _get_numeric_value(character)
        raise ValueError(f"Invalid Character[{left_pos}] = '{character}'")

    def to_check_digit(self, char_value: int) -> str:
        if 0 <= char_value <= 9:
            return str(char_value)
        raise ValueError(f"Invalid Check Digit Value ={char_value}")

    def calculate_modulus(self, code: str, includes_check_digit: bool) -> int:
        total = 0
        length = len(code)
        lth = length + (0 if includes_check_digit else 1)
        for i in range(length):
            left_pos = i + 1
            right_pos = lth - i
            char_value = self.to_int(code[i], left_pos, right_pos)
            total += self.weighted_value(char_value, left_pos, right_pos)
        if total == 0:
            raise ValueError("Invalid code, sum is zero")
        return total % self.MODULUS

    def calculate(self, code: str | None) -> str:
        if _is_blank_or_null(code):
            raise ValueError("Code is missing")
        modulus_result = self.calculate_modulus(code, False)
        char_value = (self.MODULUS - modulus_result) % self.MODULUS
        return self.to_check_digit(char_value)

    def is_valid(self, code: str | None) -> bool:
        if _is_blank_or_null(code):
            return False
        try:
            modulus_result = self.calculate_modulus(code, True)
            return modulus_result == 0
        except ValueError:
            return False


def run(operation: str, data: str | None) -> str | bool:
    luhn = LuhnCheckDigit()
    if operation == "calculate":
        return luhn.calculate(data)
    elif operation == "isValid":
        return luhn.is_valid(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
