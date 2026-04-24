"""
Mapping table: maintains consistent original → fake replacements across the document.
"""
from __future__ import annotations
import random
import re
from typing import Optional

from config.patterns import FINANCIAL_TYPES
from core.detector import PIIDetection
from mocks.names import generate_fake_name
from mocks.addresses import generate_fake_address
from mocks.phones import generate_fake_phone
from mocks.ids import (
    generate_fake_nric, generate_fake_fin, generate_fake_sg_passport,
    generate_fake_passport_generic, generate_fake_account_number,
)
from mocks.financials import scale_financial, get_random_multiplier
from mocks.entities import generate_fake_entity


class MappingTable:
    """
    Maintains a consistent mapping of original PII values to fake replacements.
    Same original value always maps to the same fake value within a session.
    """

    def __init__(self, scale_financials: bool = False, financial_multiplier: Optional[float] = None):
        self._table: dict[str, str] = {}          # normalised_original → fake
        self._type_map: dict[str, str] = {}       # normalised_original → pii_type
        self._scale_financials = scale_financials
        self._multiplier = financial_multiplier or get_random_multiplier()

    @property
    def scale_financials(self) -> bool:
        return self._scale_financials

    @scale_financials.setter
    def scale_financials(self, value: bool):
        if value != self._scale_financials:
            self._scale_financials = value
            # Clear financial mappings so they regenerate
            to_remove = [k for k, v in self._type_map.items() if v in FINANCIAL_TYPES]
            for k in to_remove:
                self._table.pop(k, None)
                self._type_map.pop(k, None)

    @property
    def multiplier(self) -> float:
        return self._multiplier

    @multiplier.setter
    def multiplier(self, value: float):
        if value != self._multiplier:
            self._multiplier = value
            # Clear financial mappings
            to_remove = [k for k, v in self._type_map.items() if v in FINANCIAL_TYPES]
            for k in to_remove:
                self._table.pop(k, None)
                self._type_map.pop(k, None)

    @staticmethod
    def _normalise(text: str) -> str:
        """Normalise whitespace for consistent keying."""
        return re.sub(r'\s+', ' ', text.strip())

    def _generate_fake(self, original: str, pii_type: str) -> str:
        """Generate a fake value for the given PII type."""
        norm = self._normalise(original)

        if pii_type == "NAME":
            return generate_fake_name(norm)

        elif pii_type == "EMAIL":
            # Build from fake name parts
            # Extract domain part if needed, but always use example.com
            local_match = re.match(r'^([^@]+)@', norm)
            local = local_match.group(1) if local_match else "user"
            # Generate a fake name to derive email parts
            fake_name = generate_fake_name(local.replace(".", " ").replace("_", " "))
            # Clean -test-data suffix for email construction then re-add
            name_parts = fake_name.replace("-test-data", "").strip().split()
            if len(name_parts) >= 2:
                email_local = f"{name_parts[0].lower()}.{name_parts[-1].lower()}-test-data"
            else:
                email_local = f"{name_parts[0].lower()}-test-data"
            return f"{email_local}@example.com"

        elif pii_type in ("PHONE_SG", "PHONE_INTL"):
            return generate_fake_phone(norm)

        elif pii_type == "DATE":
            return self._shift_date(norm)

        elif pii_type == "AGE":
            return self._shift_age(norm)

        elif pii_type == "NRIC":
            prefix = norm[0] if norm else "S"
            if prefix in ("F", "G"):
                return generate_fake_fin()
            return generate_fake_nric()

        elif pii_type == "PASSPORT_SG":
            return generate_fake_sg_passport()

        elif pii_type == "PASSPORT_GENERIC":
            return generate_fake_passport_generic(norm)

        elif pii_type in ("ACCOUNT_NUM", "BANK_ACCOUNT"):
            return generate_fake_account_number(norm)

        elif pii_type == "ENTITY_NAME":
            return generate_fake_entity(norm)

        elif pii_type in FINANCIAL_TYPES:
            if self._scale_financials:
                return scale_financial(norm, self._multiplier)
            return norm  # No change if scaling disabled

        elif pii_type == "ADDRESS_SG":
            return generate_fake_address(norm) + " (test-data)"

        elif pii_type == "POSTCODE_SG":
            from mocks.addresses import _generate_sg_postal_code
            new_code = _generate_sg_postal_code()
            # Preserve "Singapore " prefix if present in original
            if norm.lower().startswith("singapore"):
                return f"Singapore {new_code}"
            return new_code

        else:
            return norm  # Unknown type: no change

    def _shift_date(self, date_str: str) -> str:
        """Shift a date by ±3–7 years."""
        import re
        offset = random.choice([-1, 1]) * random.randint(3, 7)

        # Try dd/mm/yyyy or dd-mm-yyyy
        m = re.match(r'^(\d{1,2})([\/\-])(\d{1,2})\2(\d{2,4})$', date_str)
        if m:
            day, sep, month, year = m.group(1), m.group(2), m.group(3), m.group(4)
            new_year = int(year) + offset
            if len(year) == 2:
                new_year = new_year % 100
            return f"{day}{sep}{month}{sep}{new_year}"

        # Try "DD Mon YYYY"
        m2 = re.match(
            r'^(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{2,4})$',
            date_str, re.IGNORECASE
        )
        if m2:
            day, month_str, year = m2.group(1), m2.group(2), m2.group(3)
            new_year = int(year) + offset
            return f"{day} {month_str} {new_year}"

        # Try "Mon DD, YYYY"
        m3 = re.match(
            r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{2,4})$',
            date_str, re.IGNORECASE
        )
        if m3:
            month_str, day, year = m3.group(1), m3.group(2), m3.group(3)
            new_year = int(year) + offset
            return f"{month_str} {day}, {new_year}"

        return date_str  # Unrecognised format: return as-is

    def _shift_age(self, age_str: str) -> str:
        """Shift an age by ±3–7 years."""
        m = re.search(r'\d+', age_str)
        if m:
            original_age = int(m.group())
            offset = random.choice([-1, 1]) * random.randint(3, 7)
            new_age = max(1, original_age + offset)
            return age_str[:m.start()] + str(new_age) + age_str[m.end():]
        return age_str

    def get_or_create(self, original: str, pii_type: str) -> str:
        """Get existing mapping or create a new one."""
        norm = self._normalise(original)
        if norm not in self._table:
            # If this short token is a substring of an already-mapped longer value,
            # reuse that mapping for consistency (e.g. "CapVista" → same fake as "CapVista Technologies Pte Ltd")
            for existing_orig, existing_fake in self._table.items():
                if (norm in existing_orig and len(norm) < len(existing_orig)
                        and self._type_map.get(existing_orig) == pii_type):
                    self._table[norm] = existing_fake
                    self._type_map[norm] = pii_type
                    return existing_fake
            self._table[norm] = self._generate_fake(norm, pii_type)
            self._type_map[norm] = pii_type
        return self._table[norm]

    def get(self, original: str) -> Optional[str]:
        """Get existing mapping without creating."""
        return self._table.get(self._normalise(original))

    def set_override(self, original: str, fake: str):
        """Manually override a mapping (from UI edits)."""
        norm = self._normalise(original)
        self._table[norm] = fake

    def apply_overrides(self, overrides: dict[str, str]):
        """Apply a dict of {original: fake} overrides."""
        for orig, fake in overrides.items():
            self.set_override(orig, fake)

    def build_from_detections(self, detections: list[PIIDetection]):
        """Pre-populate the mapping table from all detections."""
        for det in detections:
            self.get_or_create(det.original_text, det.pii_type)

    def to_records(self) -> list[dict]:
        """Return mapping as a list of records for UI display."""
        records = []
        for norm_orig, fake in self._table.items():
            pii_type = self._type_map.get(norm_orig, "UNKNOWN")
            records.append({
                "PII Type": pii_type,
                "Original Value": norm_orig,
                "Proposed Replacement": fake,
                "Include": True,
            })
        return sorted(records, key=lambda r: r["PII Type"])

    def items(self) -> list[tuple[str, str]]:
        """Return (original, fake) pairs sorted by length desc (for replacement order)."""
        return sorted(self._table.items(), key=lambda x: len(x[0]), reverse=True)

    def __len__(self) -> int:
        return len(self._table)
