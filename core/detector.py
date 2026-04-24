"""
PII detection: regex patterns + spaCy NER fusion.
Returns a list of PIIDetection objects sorted by page and character position.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import re

from config.patterns import PATTERNS, FINANCIAL_TYPES, DATE_TYPES, ID_TYPES, PHONE_TYPES
from core.extractor import DocumentContent


@dataclass
class PIIDetection:
    original_text: str
    pii_type: str
    source: str          # "regex" or "ner"
    page_num: int
    char_start: int      # character offset within the page's raw_text
    char_end: int

    def __hash__(self):
        return hash((self.original_text, self.pii_type, self.page_num, self.char_start))


# spaCy label → our PII type
_SPACY_LABEL_MAP = {
    "PERSON": "NAME",
    "ORG": "ENTITY_NAME",
    "GPE": "ADDRESS_FRAGMENT",
    "LOC": "ADDRESS_FRAGMENT",
    "DATE": "DATE",
    "CARDINAL": None,  # skip
    "MONEY": "FINANCIAL_GENERIC",
}

# PII types to skip from spaCy (already handled by regex)
_SKIP_NER_TYPES = FINANCIAL_TYPES | DATE_TYPES | ID_TYPES | PHONE_TYPES | {"EMAIL", "POSTCODE_SG"}


def _regex_detect_page(text: str, page_num: int) -> tuple[list[PIIDetection], set[tuple[int, int]]]:
    """Run all regex patterns against page text. Returns detections and claimed spans."""
    detections: list[PIIDetection] = []
    claimed: set[tuple[int, int]] = set()  # (start, end) of already-matched spans

    for pii_type, pattern, _priority in PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            # Check overlap with already-claimed spans
            overlaps = any(
                not (end <= cs or start >= ce)
                for cs, ce in claimed
            )
            if not overlaps:
                detections.append(PIIDetection(
                    original_text=match.group(),
                    pii_type=pii_type,
                    source="regex",
                    page_num=page_num,
                    char_start=start,
                    char_end=end,
                ))
                claimed.add((start, end))

    return detections, claimed


def _ner_detect_page(text: str, page_num: int, claimed: set[tuple[int, int]], nlp) -> list[PIIDetection]:
    """Run spaCy NER on page text, skipping already-claimed spans."""
    if not text.strip():
        return []

    detections: list[PIIDetection] = []
    try:
        doc = nlp(text)
    except Exception:
        return []

    for ent in doc.ents:
        pii_type = _SPACY_LABEL_MAP.get(ent.label_)
        if pii_type is None:
            continue
        if pii_type in _SKIP_NER_TYPES:
            continue

        start, end = ent.start_char, ent.end_char
        # Skip if overlaps with regex claims
        overlaps = any(
            not (end <= cs or start >= ce)
            for cs, ce in claimed
        )
        ent_text = ent.text.strip()
        # Skip: too short, contains newlines, or is a common non-name word
        _SKIP_WORDS = {
            "email", "date", "name", "address", "mobile", "phone", "fax",
            "portfolio", "account", "total", "aum", "company", "ref",
            "manager", "client", "profile", "mr", "mrs", "ms", "dr",
        }
        if (not overlaps
                and len(ent_text) > 1
                and "\n" not in ent_text
                and ent_text.lower() not in _SKIP_WORDS):
            detections.append(PIIDetection(
                original_text=ent_text,
                pii_type=pii_type,
                source="ner",
                page_num=page_num,
                char_start=start,
                char_end=end,
            ))

    return detections


def detect(document: DocumentContent, use_spacy: bool = True) -> list[PIIDetection]:
    """
    Detect all PII across the document.
    Returns detections sorted by (page_num, char_start).
    """
    all_detections: list[PIIDetection] = []
    nlp = None

    if use_spacy:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            use_spacy = False

    for page in document.pages:
        text = page.raw_text or ""
        regex_detections, claimed_spans = _regex_detect_page(text, page.page_num)
        all_detections.extend(regex_detections)

        if use_spacy and nlp:
            ner_detections = _ner_detect_page(text, page.page_num, claimed_spans, nlp)
            all_detections.extend(ner_detections)

    # Sort by page, then by position
    all_detections.sort(key=lambda d: (d.page_num, d.char_start))

    # Deduplicate (same text, type, page, position)
    seen = set()
    unique: list[PIIDetection] = []
    for d in all_detections:
        key = (d.page_num, d.char_start, d.char_end)
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return unique
