import unicodedata
from typing import Any


def _is_blank_or_null(code: str | None) -> bool:
    if code is None:
        return True
    trimmed = code.strip("\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f ")
    return len(trimmed) == 0


def _to_utf16_chars(s: str) -> list[str]:
    raw_bytes = s.encode('utf-16-be')
    chars = []
    for i in range(0, len(raw_bytes), 2):
        val = (raw_bytes[i] << 8) | raw_bytes[i + 1]
        chars.append(chr(val))
    return chars


class LuhnCheckDigit:
    MODULUS = 10
    POSITION_WEIGHT = [2, 1]

    def weighted_value(self, char_value: int, left_pos: int, right_pos: int) -> int:
        weight = self.POSITION_WEIGHT[right_pos % 2]
        weighted = char_value * weight
        return weighted - 9 if weighted > 9 else weighted

    def to_int(self, character: str, left_pos: int, right_pos: int) -> int:
        if unicodedata.category(character) == 'Nd':
            return unicodedata.decimal(character)
        raise ValueError(f"Invalid Character[{left_pos}] = '{character}'")

    def to_check_digit(self, char_value: int) -> str:
        if 0 <= char_value <= 9:
            return str(char_value)
        raise ValueError(f"Invalid Check Digit Value ={char_value}")

    def calculate_modulus(self, code: str, includes_check_digit: bool) -> int:
        chars = _to_utf16_chars(code)
        length = len(chars)
        lth = length + (0 if includes_check_digit else 1)
        total = 0
        for i in range(length):
            left_pos = i + 1
            right_pos = lth - i
            char_value = self.to_int(chars[i], left_pos, right_pos)
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


def run(operation: str, data: Any) -> Any:
    luhn = LuhnCheckDigit()
    if operation == "calculate":
        return luhn.calculate(data)
    elif operation == "isValid":
        return luhn.is_valid(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
