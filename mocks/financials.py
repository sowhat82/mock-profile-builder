"""
Financial figure anonymisation: parse and scale monetary values.
"""
import re
import random


def parse_financial_value(text: str) -> tuple[str, float, str]:
    """
    Parse a financial string into (currency_prefix, numeric_value, decimal_str).
    Returns (prefix, value, decimal_places_str).
    """
    # Extract currency prefix
    prefix_match = re.match(r'^(S?\$|US?\$|£|€|¥|RM|HK\$)?\s*', text)
    prefix = prefix_match.group(1) or "" if prefix_match else ""

    # Extract numeric part
    numeric_str = re.sub(r'[^\d.,]', '', text)
    numeric_str = numeric_str.replace(',', '')

    # Detect decimal places
    if '.' in numeric_str:
        parts = numeric_str.split('.')
        decimal_places = len(parts[1])
        value = float(numeric_str)
    else:
        decimal_places = 0
        value = float(numeric_str) if numeric_str else 0.0

    return prefix, value, decimal_places


def format_financial_value(prefix: str, value: float, decimal_places: int, original: str) -> str:
    """Format a value back to match the original's style."""
    # Detect if original used comma separators
    use_commas = ',' in original

    if decimal_places > 0:
        fmt_value = f"{value:,.{decimal_places}f}" if use_commas else f"{value:.{decimal_places}f}"
    else:
        int_value = round(value)
        fmt_value = f"{int_value:,}" if use_commas else str(int_value)

    return f"{prefix}{fmt_value}"


def scale_financial(original: str, multiplier: float) -> str:
    """Scale a financial figure by the given multiplier, preserving format."""
    try:
        prefix, value, decimal_places = parse_financial_value(original)
        new_value = value * multiplier
        return format_financial_value(prefix, new_value, decimal_places, original)
    except (ValueError, AttributeError):
        return original


def get_random_multiplier() -> float:
    """Generate a random scale multiplier between 0.5x and 2x."""
    return round(random.uniform(0.5, 2.0), 4)
