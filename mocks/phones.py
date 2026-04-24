"""
Phone number anonymisation: generates structurally valid fake numbers.
"""
import random
import re


def _preserve_format(original: str, new_digits: str) -> str:
    """Preserve the formatting (spaces, dashes) of the original number."""
    # Extract formatting characters
    fmt = re.sub(r'\d', '{}', original)
    digits_iter = iter(new_digits)
    try:
        return fmt.format(*digits_iter)
    except (IndexError, KeyError):
        return new_digits


def _generate_sg_mobile() -> str:
    """Generate a valid-format SG mobile number (8xxx or 9xxx)."""
    prefix = random.choice(["8", "9"])
    rest = str(random.randint(0, 9999999)).zfill(7)
    return prefix + rest


def _generate_sg_landline() -> str:
    """Generate a valid-format SG landline (6xxx xxxx)."""
    rest = str(random.randint(0, 9999999)).zfill(7)
    return "6" + rest


def generate_fake_phone(original: str) -> str:
    """Generate a structurally valid fake phone number matching the original's country/format."""
    original_stripped = re.sub(r'[\s\-\(\)]', '', original)

    # Detect country code
    if original_stripped.startswith("+65") or re.match(r'^[689]\d{7}$', original_stripped):
        # Singapore
        new_digits = _generate_sg_mobile() if random.random() > 0.3 else _generate_sg_landline()
        # Preserve +65 prefix if present
        if "+65" in original:
            # Detect if spaces or dashes used
            sep = " " if " " in original.replace("+65", "", 1) else ""
            if sep:
                return f"+65 {new_digits[:4]} {new_digits[4:]}"
            return f"+65{new_digits}"
        # Plain 8-digit
        if " " in original.strip():
            return f"{new_digits[:4]} {new_digits[4:]}"
        return new_digits

    elif original_stripped.startswith("+60"):
        # Malaysia
        new_digits = str(random.randint(10000000000, 19999999999))
        return f"+60 {new_digits[1:3]}-{new_digits[3:7]} {new_digits[7:]}"

    elif original_stripped.startswith("+1"):
        # North America
        area = str(random.randint(200, 999))
        mid = str(random.randint(200, 999))
        end = str(random.randint(1000, 9999))
        return f"+1 ({area}) {mid}-{end}"

    elif original_stripped.startswith("+44"):
        # UK
        new_digits = str(random.randint(7000000000, 7999999999))
        return f"+44 7{new_digits[1:4]} {new_digits[4:7]} {new_digits[7:]}"

    else:
        # Generic: keep country code, randomise the rest
        cc_match = re.match(r'(\+\d{1,3})(.*)', original)
        if cc_match:
            cc = cc_match.group(1)
            rest_len = len(re.sub(r'\D', '', cc_match.group(2)))
            new_rest = str(random.randint(10**(rest_len-1), 10**rest_len - 1))
            return f"{cc} {new_rest}"
        # Fallback: random 8-digit
        return str(random.randint(80000000, 99999999))
