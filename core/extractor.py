"""
PDF text extraction using pdfplumber.
Preserves layout metadata (bounding boxes, font info) per word.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import io
import pdfplumber


@dataclass
class WordInfo:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    font_size: float = 10.0
    fontname: str = "Helvetica"
    bold: bool = False
    italic: bool = False


@dataclass
class LineInfo:
    """A line of text reconstructed from word bounding boxes."""
    words: list[WordInfo] = field(default_factory=list)
    y0: float = 0.0
    y1: float = 0.0

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def x0(self) -> float:
        return self.words[0].x0 if self.words else 0.0


@dataclass
class PageContent:
    page_num: int
    raw_text: str
    words: list[WordInfo] = field(default_factory=list)
    lines: list[LineInfo] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    width: float = 595.0   # A4 default
    height: float = 842.0  # A4 default


@dataclass
class DocumentContent:
    pages: list[PageContent] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.raw_text for p in self.pages if p.raw_text)


def _parse_font_info(char_dict: dict) -> tuple[float, str, bool, bool]:
    """Extract font size, name, bold, italic from a pdfplumber char dict."""
    fontname = char_dict.get("fontname", "Helvetica")
    size = float(char_dict.get("size", 10.0))
    bold = "Bold" in fontname or "bold" in fontname
    italic = any(x in fontname for x in ["Italic", "italic", "Oblique", "oblique"])
    return size, fontname, bold, italic


def _words_to_lines(words: list[WordInfo], y_tolerance: float = 3.0) -> list[LineInfo]:
    """Group words into lines by Y-coordinate proximity."""
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (round(w.y0 / y_tolerance), w.x0))
    lines: list[LineInfo] = []
    current_line: list[WordInfo] = [sorted_words[0]]

    for word in sorted_words[1:]:
        prev = current_line[-1]
        # Same line if Y positions are close
        if abs(word.y0 - prev.y0) <= y_tolerance:
            current_line.append(word)
        else:
            y_vals = [w.y0 for w in current_line]
            y_max_vals = [w.y1 for w in current_line]
            lines.append(LineInfo(
                words=current_line,
                y0=min(y_vals),
                y1=max(y_max_vals),
            ))
            current_line = [word]

    if current_line:
        y_vals = [w.y0 for w in current_line]
        y_max_vals = [w.y1 for w in current_line]
        lines.append(LineInfo(
            words=current_line,
            y0=min(y_vals),
            y1=max(y_max_vals),
        ))

    return lines


def extract(pdf_bytes: bytes) -> DocumentContent:
    """Extract text, layout, and tables from a PDF."""
    doc = DocumentContent()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract raw text
            raw_text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""

            # Extract word-level bounding boxes with font info
            words: list[WordInfo] = []
            try:
                plumber_words = page.extract_words(
                    x_tolerance=2,
                    y_tolerance=3,
                    extra_attrs=["fontname", "size"],
                    keep_blank_chars=False,
                )
                for w in plumber_words:
                    fontname = w.get("fontname", "Helvetica")
                    size = float(w.get("size", 10.0))
                    bold = "Bold" in fontname or "bold" in fontname
                    italic = any(x in fontname for x in ["Italic", "italic", "Oblique"])
                    words.append(WordInfo(
                        text=w["text"],
                        x0=w["x0"],
                        y0=w["top"],
                        x1=w["x1"],
                        y1=w["bottom"],
                        page_num=page_num,
                        font_size=size,
                        fontname=fontname,
                        bold=bold,
                        italic=italic,
                    ))
            except Exception:
                # Fallback: no bounding box info
                pass

            # Extract tables
            tables: list[list[list[str]]] = []
            try:
                extracted_tables = page.extract_tables()
                if extracted_tables:
                    for table in extracted_tables:
                        cleaned = [
                            [cell or "" for cell in row]
                            for row in table
                            if row
                        ]
                        tables.append(cleaned)
            except Exception:
                pass

            lines = _words_to_lines(words)

            page_content = PageContent(
                page_num=page_num,
                raw_text=raw_text,
                words=words,
                lines=lines,
                tables=tables,
                width=float(page.width),
                height=float(page.height),
            )
            doc.pages.append(page_content)

    return doc
