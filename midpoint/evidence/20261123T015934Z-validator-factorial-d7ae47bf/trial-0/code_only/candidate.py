import unicodedata

class CheckDigitException(Exception):
    pass

def _is_blank_or_null(code: str | None) -> bool:
    if code is None:
        return True
    trimmed = code.strip(''.join(chr(i) for i in range(33)))
    return len(trimmed) == 0

class LuhnCheckDigit:
    POSITION_WEIGHT = [2, 1]
    MODULUS = 10

    def weighted_value(self, char_value: int, left_pos: int, right_pos: int) -> int:
        weight = self.POSITION_WEIGHT[right_pos % 2]
        weighted_val = char_value * weight
        return weighted_val - 9 if weighted_val > 9 else weighted_val

    def to_int(self, char_unit: int, left_pos: int, right_pos: int) -> int:
        char_str = chr(char_unit)
        if unicodedata.category(char_str) == 'Nd':
            return unicodedata.digit(char_str)
        raise CheckDigitException(f"Invalid Character[{left_pos}] = '{char_str}'")

    def to_check_digit(self, char_value: int) -> str:
        if 0 <= char_value <= 9:
            return str(char_value)
        raise CheckDigitException(f"Invalid Check Digit Value ={char_value}")

    def calculate_modulus(self, code: str, includes_check_digit: bool) -> int:
        raw_bytes = code.encode('utf-16-le')
        units = [raw_bytes[i] | (raw_bytes[i + 1] << 8) for i in range(0, len(raw_bytes), 2)]
        code_len = len(units)
        total = 0
        for i in range(code_len):
            lth = code_len + (0 if includes_check_digit else 1)
            left_pos = i + 1
            right_pos = lth - i
            char_val = self.to_int(units[i], left_pos, right_pos)
            total += self.weighted_value(char_val, left_pos, right_pos)
        if total == 0:
            raise CheckDigitException("Invalid code, sum is zero")
        return total % self.MODULUS

    def calculate(self, code: str | None) -> str:
        if _is_blank_or_null(code):
            raise CheckDigitException("Code is missing")
        modulus_result = self.calculate_modulus(code, False)
        char_value = (self.MODULUS - modulus_result) % self.MODULUS
        return self.to_check_digit(char_value)

    def is_valid(self, code: str | None) -> bool:
        if _is_blank_or_null(code):
            return False
        try:
            modulus_result = self.calculate_modulus(code, True)
            return modulus_result == 0
        except CheckDigitException:
            return False

def run(operation: str, data: str | None):
    luhn = LuhnCheckDigit()
    if operation == "calculate":
        try:
            return luhn.calculate(data)
        except CheckDigitException as e:
            raise ValueError(str(e)) from e
    elif operation == "isValid":
        return luhn.is_valid(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
