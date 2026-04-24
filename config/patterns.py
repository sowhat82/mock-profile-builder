"""
Regex patterns for PII detection, ordered by specificity (most specific first).
Singapore wealth management context.
"""
import re

# Each entry: (pii_type, compiled_regex, priority)
# Lower priority number = runs first
PATTERNS = [
    # --- Emails (high specificity — match before generic text) ---
    ("EMAIL", re.compile(
        r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'
    ), 10),

    # --- Singapore NRIC / FIN ---
    ("NRIC", re.compile(
        r'\b[STFGM]\d{7}[A-Z]\b'
    ), 20),

    # --- Singapore passport ---
    ("PASSPORT_SG", re.compile(
        r'\bE\d{7}[A-Z]\b'
    ), 21),

    # --- Generic passport (letter + 7-9 digits + optional letter) ---
    ("PASSPORT_GENERIC", re.compile(
        r'\b[A-Z]{1,2}\d{6,9}[A-Z]?\b'
    ), 22),

    # --- Singapore phone numbers ---
    ("PHONE_SG", re.compile(
        r'(?:\+65[\s\-]?)?(?<!\d)[689]\d{3}[\s\-]?\d{4}(?!\d)'
    ), 30),

    # --- International phone numbers ---
    ("PHONE_INTL", re.compile(
        r'\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}'
    ), 31),

    # --- Dates (dd/mm/yyyy, dd-mm-yyyy, dd MMM yyyy) ---
    ("DATE", re.compile(
        r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b'
        r'|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4}\b'
        r'|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}\b',
        re.IGNORECASE
    ), 40),

    # --- Ages ---
    ("AGE", re.compile(
        r'\b(?:age[d]?\s*:?\s*|aged\s+)\d{1,3}\b',
        re.IGNORECASE
    ), 41),

    # --- Account / portfolio numbers ---
    ("ACCOUNT_NUM", re.compile(
        r'\b(?:P|ACC|AC|REF|A\/C)[\-\s]?\d{6,12}\b',
        re.IGNORECASE
    ), 50),

    ("BANK_ACCOUNT", re.compile(
        r'\b\d{3}[\-\s]\d{5,7}[\-\s]\d{1,3}\b'
    ), 51),

    # --- SGD financial figures ---
    ("FINANCIAL_SGD", re.compile(
        r'S?\$\s?[\d,]+(?:\.\d{2})?\b'
    ), 60),

    # --- USD / other currency figures ---
    ("FINANCIAL_USD", re.compile(
        r'US?\$\s?[\d,]+(?:\.\d{2})?\b'
    ), 61),

    # --- Generic large numbers (potentially financial) ---
    ("FINANCIAL_GENERIC", re.compile(
        r'\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b'
    ), 62),

    # --- Singapore street address (full: street + unit + postal code) — runs before standalone postcode ---
    # Uses [ -] not \s in the name portion to prevent matching across newlines.
    # \b after street type prevents "St" from matching inside words like "institutions".
    ("ADDRESS_SG", re.compile(
        r'\d+[A-Za-z]?\s+[A-Za-z][A-Za-z -]+?'
        r'(?:Road|Street|Avenue|Drive|Lane|Crescent|Close|Way|Boulevard|Rise|Walk|View|Hill|Place|Garden|Ave|Rd|St|Dr)\b'
        r'(?:,?\s*#\d{2,3}-\d{2,4})?'
        r'(?:,?\s*Singapore\s+\d{6})?',
        re.IGNORECASE
    ), 69),

    # --- Singapore postal codes (standalone, not already part of an ADDRESS_SG match) ---
    ("POSTCODE_SG", re.compile(
        r'(?:Singapore\s+)?\b[0-9]{6}\b(?!\s*\-|\d)'
    ), 70),
]

# Sort by priority
PATTERNS.sort(key=lambda x: x[2])

# PII types that represent financial figures
FINANCIAL_TYPES = {"FINANCIAL_SGD", "FINANCIAL_USD", "FINANCIAL_GENERIC"}

# PII types that represent dates/ages (need date shifting)
DATE_TYPES = {"DATE", "AGE"}

# PII types that represent identity numbers
ID_TYPES = {"NRIC", "PASSPORT_SG", "PASSPORT_GENERIC"}

# PII types for phone numbers
PHONE_TYPES = {"PHONE_SG", "PHONE_INTL"}
