# Deterministic assisted portability repair; original model candidate archived.
def _java_decimal_portable(character):
    value = ord(character)
    for base in (48, 1632, 1776, 1984, 2406, 2534, 2662, 2790, 2918, 3046, 3174, 3302, 3430, 3558, 3664, 3792, 3872, 4160, 4240, 6112, 6160, 6470, 6608, 6784, 6800, 6992, 7088, 7232, 7248, 42528, 43216, 43264, 43472, 43504, 43600, 44016, 65296):
        if base <= value < base + 10:
            return value - base
    raise ValueError("Not a Java decimal char")

import unicodedata
from typing import Any

def _to_utf16_chars(code: str) -> list[str]:
    raw_bytes = code.encode('utf-16-be')
    return [chr(raw_bytes[i] * 256 + raw_bytes[i + 1]) for i in range(0, len(raw_bytes), 2)]

def _is_blank_or_null(code: str | None) -> bool:
    if code is None:
        return True
    chars = _to_utf16_chars(code)
    start = 0
    end = len(chars)
    while start < end and ord(chars[start]) <= 32:
        start += 1
    while end > start and ord(chars[end - 1]) <= 32:
        end -= 1
    return end - start == 0

class LuhnCheckDigit:
    MODULUS = 10
    POSITION_WEIGHT = [2, 1]

    def weighted_value(self, char_value: int, left_pos: int, right_pos: int) -> int:
        weight = self.POSITION_WEIGHT[right_pos % 2]
        weighted = char_value * weight
        return weighted - 9 if weighted > 9 else weighted

    def to_int(self, character: str, left_pos: int, right_pos: int) -> int:
        if unicodedata.category(character) == 'Nd':
            return _java_decimal_portable(character)
        raise ValueError(f"Invalid Character[{left_pos}] = '{character}'")

    def to_check_digit(self, char_value: int) -> str:
        if 0 <= char_value <= 9:
            return str(char_value)
        raise ValueError(f'Invalid Check Digit Value ={char_value}')

    def calculate_modulus(self, chars: list[str], includes_check_digit: bool) -> int:
        total = 0
        length = len(chars)
        lth = length + (0 if includes_check_digit else 1)
        for i in range(length):
            left_pos = i + 1
            right_pos = lth - i
            char_value = self.to_int(chars[i], left_pos, right_pos)
            total += self.weighted_value(char_value, left_pos, right_pos)
        if total == 0:
            raise ValueError('Invalid code, sum is zero')
        return total % self.MODULUS

    def calculate(self, code: str | None) -> str:
        if _is_blank_or_null(code):
            raise ValueError('Code is missing')
        chars = _to_utf16_chars(code)
        modulus_result = self.calculate_modulus(chars, False)
        char_value = (self.MODULUS - modulus_result) % self.MODULUS
        return self.to_check_digit(char_value)

    def is_valid(self, code: str | None) -> bool:
        if _is_blank_or_null(code):
            return False
        try:
            chars = _to_utf16_chars(code)
            modulus_result = self.calculate_modulus(chars, True)
            return modulus_result == 0
        except ValueError:
            return False

def run(operation: str, data: str | None) -> Any:
    luhn = LuhnCheckDigit()
    if operation == 'calculate':
        return luhn.calculate(data)
    elif operation == 'isValid':
        return luhn.is_valid(data)
    else:
        raise ValueError(f'Unknown operation: {operation}')
