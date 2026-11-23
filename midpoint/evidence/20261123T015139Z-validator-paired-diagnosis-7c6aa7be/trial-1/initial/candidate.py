import unicodedata

class CheckDigitException(Exception):
    pass

def _is_blank_or_null(code: str | None) -> bool:
    if code is None:
        return True
    return len(code.strip()) == 0

def _to_utf16_code_units(s: str) -> list[int]:
    res = []
    for ch in s:
        cp = ord(ch)
        if cp <= 0xFFFF:
            res.append(cp)
        else:
            cp_prime = cp - 0x10000
            res.append(0xD800 + (cp_prime >> 10))
            res.append(0xDC00 + (cp_prime & 0x3FF))
    return res

class LuhnCheckDigit:
    POSITION_WEIGHT = [2, 1]
    MODULUS = 10

    def weighted_value(self, char_value: int, left_pos: int, right_pos: int) -> int:
        weight = self.POSITION_WEIGHT[right_pos % 2]
        weighted_val = char_value * weight
        return weighted_val - 9 if weighted_val > 9 else weighted_val

    def _to_int(self, character: str, left_pos: int, right_pos: int) -> int:
        if len(character) == 1 and ('0' <= character <= '9'):
            return ord(character) - ord('0')
        raise CheckDigitException(f"Invalid Character[{left_pos}] = '{character}'")

    def _to_check_digit(self, char_value: int) -> str:
        if 0 <= char_value <= 9:
            return str(char_value)
        raise CheckDigitException(f"Invalid Check Digit Value ={char_value}")

    def _calculate_modulus(self, code: str, includes_check_digit: bool) -> int:
        code_units = _to_utf16_code_units(code)
        lth = len(code_units) + (0 if includes_check_digit else 1)
        total = 0
        for i, cu in enumerate(code_units):
            left_pos = i + 1
            right_pos = lth - i
            ch_str = chr(cu)
            char_val = self._to_int(ch_str, left_pos, right_pos)
            total += self.weighted_value(char_val, left_pos, right_pos)
        if total == 0:
            raise CheckDigitException("Invalid code, sum is zero")
        return total % self.MODULUS

    def calculate(self, code: str | None) -> str:
        if _is_blank_or_null(code):
            raise CheckDigitException("Code is missing")
        modulus_result = self._calculate_modulus(code, False)
        char_value = (self.MODULUS - modulus_result) % self.MODULUS
        return self._to_check_digit(char_value)

    def is_valid(self, code: str | None) -> bool:
        if _is_blank_or_null(code):
            return False
        try:
            modulus_result = self._calculate_modulus(code, True)
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
