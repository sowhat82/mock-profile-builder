"""
Identity document number anonymisation.
Generates structurally valid but fake ID numbers.
"""
import random
import string


# NRIC check character computation (Singapore)
_NRIC_WEIGHTS = [2, 7, 6, 5, 4, 3, 2]
_NRIC_CHECK_ST = "JZIHGFEDCBA"
_NRIC_CHECK_FG = "XWUTRQPNMLK"


def _compute_nric_check(prefix: str, digits: str) -> str:
    """Compute the NRIC check character."""
    total = sum(int(d) * w for d, w in zip(digits, _NRIC_WEIGHTS))
    if prefix in ("T", "G"):
        total += 4
    elif prefix == "M":
        total += 3
    idx = total % 11
    if prefix in ("S", "T"):
        return _NRIC_CHECK_ST[idx]
    else:
        return _NRIC_CHECK_FG[idx]


def generate_fake_nric() -> str:
    """Generate a structurally valid but fake Singapore NRIC/FIN."""
    prefix = random.choice(["S", "T"])
    digits = "".join(str(random.randint(0, 9)) for _ in range(7))
    check = _compute_nric_check(prefix, digits)
    return f"{prefix}{digits}{check}"


def generate_fake_fin() -> str:
    """Generate a structurally valid but fake Singapore FIN (foreign ID)."""
    prefix = random.choice(["F", "G"])
    digits = "".join(str(random.randint(0, 9)) for _ in range(7))
    check = _compute_nric_check(prefix, digits)
    return f"{prefix}{digits}{check}"


def generate_fake_sg_passport() -> str:
    """Generate a fake Singapore passport number (E + 7 digits + letter)."""
    digits = "".join(str(random.randint(0, 9)) for _ in range(7))
    check = random.choice(string.ascii_uppercase)
    return f"E{digits}{check}"


def generate_fake_passport_generic(original: str) -> str:
    """Generate a generic fake passport matching the original's format."""
    import re
    # Preserve the leading letter(s) count and digit count
    letter_prefix = re.match(r'^([A-Z]+)', original)
    digit_part = re.search(r'(\d+)', original)
    letter_suffix = re.search(r'([A-Z])$', original)

    prefix = letter_prefix.group(1) if letter_prefix else "X"
    new_prefix = "".join(random.choice(string.ascii_uppercase) for _ in prefix)

    n_digits = len(digit_part.group(1)) if digit_part else 7
    new_digits = "".join(str(random.randint(0, 9)) for _ in range(n_digits))

    suffix = random.choice(string.ascii_uppercase) if letter_suffix else ""
    return f"{new_prefix}{new_digits}{suffix}"


def generate_fake_account_number(original: str) -> str:
    """Generate a fake account/portfolio number with the same format."""
    import re
    # Preserve letter prefix and separators
    result = re.sub(r'\d', lambda m: str(random.randint(0, 9)), original)
    return result
