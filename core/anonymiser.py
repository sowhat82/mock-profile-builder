"""
Apply PII replacements to document text using the mapping table.
Processes right-to-left to preserve character offsets.
"""
from __future__ import annotations
import re

from core.extractor import DocumentContent, PageContent, WordInfo
from core.mapper import MappingTable
from core.detector import PIIDetection


def anonymise_text(text: str, mapping_table: MappingTable, excluded_originals: set[str] = None) -> str:
    """
    Replace all PII in text using the mapping table.
    Uses longest-match-first to avoid partial replacements.
    """
    if not text:
        return text

    excluded = excluded_originals or set()

    # Build sorted list of (original, fake) pairs — longest first to avoid partial matches
    replacements = [
        (orig, fake)
        for orig, fake in mapping_table.items()
        if orig not in excluded and fake != orig
    ]

    if not replacements:
        return text

    result = text
    for original, fake in replacements:
        if not original:
            continue
        # Use word-boundary-aware replacement where possible
        try:
            # Escape special regex chars in original
            escaped = re.escape(original)
            result = re.sub(escaped, fake, result)
        except re.error:
            result = result.replace(original, fake)

    return result


def anonymise_document(
    document: DocumentContent,
    mapping_table: MappingTable,
    excluded_originals: set[str] = None,
) -> DocumentContent:
    """
    Return a new DocumentContent with all PII replaced in text and words.
    Preserves layout metadata.
    """
    from copy import deepcopy
    from dataclasses import replace as dc_replace

    excluded = excluded_originals or set()
    anonymised_doc = DocumentContent()

    for page in document.pages:
        # Anonymise raw text
        anon_text = anonymise_text(page.raw_text or "", mapping_table, excluded)

        # Anonymise word-level text (preserving bounding boxes)
        anon_words: list[WordInfo] = []
        for word in page.words:
            new_text = word.text
            for orig, fake in mapping_table.items():
                if orig in excluded or fake == orig:
                    continue
                if orig in new_text or orig.lower() in new_text.lower():
                    try:
                        new_text = re.sub(re.escape(orig), fake, new_text)
                    except re.error:
                        new_text = new_text.replace(orig, fake)
            anon_words.append(WordInfo(
                text=new_text,
                x0=word.x0,
                y0=word.y0,
                x1=word.x1,
                y1=word.y1,
                page_num=word.page_num,
                font_size=word.font_size,
                fontname=word.fontname,
                bold=word.bold,
                italic=word.italic,
            ))

        # Anonymise tables
        anon_tables = []
        for table in page.tables:
            anon_table = []
            for row in table:
                anon_row = [anonymise_text(cell, mapping_table, excluded) for cell in row]
                anon_table.append(anon_row)
            anon_tables.append(anon_table)

        from core.extractor import _words_to_lines
        anon_lines = _words_to_lines(anon_words)

        anon_page = PageContent(
            page_num=page.page_num,
            raw_text=anon_text,
            words=anon_words,
            lines=anon_lines,
            tables=anon_tables,
            width=page.width,
            height=page.height,
        )
        anonymised_doc.pages.append(anon_page)

    return anonymised_doc
