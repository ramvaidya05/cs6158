def run(a, b, operation, parameter=None):
    val_a = int(a)
    val_b = int(b)
    res = (val_a + val_b) & 0xFFFFFFFF
    if res >= 0x80000000:
        res -= 0x100000000
    return res