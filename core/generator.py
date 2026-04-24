"""
PDF generation using reportlab.
Reconstructs a clean, readable approximation of the original layout.
"""
from __future__ import annotations
import io
import re
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
pt = 1.0  # reportlab's internal unit is already points
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas as rl_canvas

from core.extractor import DocumentContent, PageContent, LineInfo, WordInfo


# Map pdfplumber/PDF font names to reportlab built-ins
_FONT_MAP = {
    "helvetica": "Helvetica",
    "times": "Times-Roman",
    "courier": "Courier",
    "arial": "Helvetica",
    "calibri": "Helvetica",
    "verdana": "Helvetica",
    "garamond": "Times-Roman",
    "georgia": "Times-Roman",
}


def _map_font(fontname: str, bold: bool, italic: bool) -> str:
    """Map a PDF font name to the nearest reportlab built-in."""
    fn_lower = fontname.lower()
    base = "Helvetica"
    for key, mapped in _FONT_MAP.items():
        if key in fn_lower:
            base = mapped
            break

    if bold and italic:
        suffix = "-BoldOblique" if base == "Helvetica" else "-BoldItalic"
    elif bold:
        suffix = "-Bold"
    elif italic:
        suffix = "-Oblique" if base == "Helvetica" else "-Italic"
    else:
        suffix = ""

    return base + suffix


def _line_to_paragraph(line: LineInfo, page_width: float) -> Optional[Paragraph]:
    """Convert a LineInfo to a reportlab Paragraph with approximate styling."""
    if not line.words:
        return None

    # Use the dominant word's font info
    dominant = max(line.words, key=lambda w: w.font_size)
    fontname = _map_font(dominant.fontname, dominant.bold, dominant.italic)
    font_size = max(6, min(dominant.font_size, 36))

    # Build HTML-escaped text with inline bold/italic spans
    parts = []
    for word in line.words:
        text = word.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        fn = _map_font(word.fontname, word.bold, word.italic)
        # Only wrap in span if different from dominant
        if fn != fontname:
            if word.bold and word.italic:
                text = f"<b><i>{text}</i></b>"
            elif word.bold:
                text = f"<b>{text}</b>"
            elif word.italic:
                text = f"<i>{text}</i>"
        parts.append(text)

    text_content = " ".join(parts)
    if not text_content.strip():
        return None

    # Estimate alignment from X position
    x_mid = (line.x0 + (line.words[-1].x1 if line.words else line.x0)) / 2
    page_mid = page_width / 2
    if abs(x_mid - page_mid) < page_width * 0.1:
        alignment = TA_CENTER
    elif line.x0 > page_width * 0.5:
        alignment = TA_RIGHT
    else:
        alignment = TA_LEFT

    style = ParagraphStyle(
        name="auto",
        fontName=fontname,
        fontSize=font_size,
        leading=font_size * 1.3,
        alignment=alignment,
        leftIndent=max(0, line.x0 - 40),  # Approximate left indent
        spaceAfter=2,
    )

    try:
        return Paragraph(text_content, style)
    except Exception:
        # Fallback: plain text
        plain_style = ParagraphStyle(
            name="plain",
            fontName="Helvetica",
            fontSize=10,
            leading=13,
        )
        plain_text = " ".join(w.text for w in line.words)
        return Paragraph(plain_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), plain_style)


def _build_table_element(table_data: list[list[str]]) -> Optional[Table]:
    """Build a reportlab Table from extracted table data."""
    if not table_data:
        return None

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        name="cell",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        wordWrap="CJK",
    )

    # Convert cells to Paragraphs for proper wrapping
    formatted_data = []
    for row in table_data:
        formatted_row = []
        for cell in row:
            cell_text = str(cell or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            try:
                formatted_row.append(Paragraph(cell_text, cell_style))
            except Exception:
                formatted_row.append(str(cell or ""))
        formatted_data.append(formatted_row)

    if not formatted_data:
        return None

    n_cols = max(len(row) for row in formatted_data)
    col_width = 480 / max(n_cols, 1)

    table = Table(formatted_data, colWidths=[col_width] * n_cols)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
    ]))
    return table


def generate_pdf(document: DocumentContent) -> bytes:
    """
    Generate an anonymised PDF from the DocumentContent.
    Returns PDF as bytes.
    """
    buf = io.BytesIO()

    # Use first page dimensions or default to A4
    if document.pages:
        first_page = document.pages[0]
        page_w = first_page.width * pt
        page_h = first_page.height * pt
        page_size = (page_w, page_h)
    else:
        page_size = A4

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    story = []
    styles = getSampleStyleSheet()

    for page_idx, page in enumerate(document.pages):
        if page_idx > 0:
            story.append(PageBreak())

        if page.lines:
            # Use layout-aware line reconstruction
            prev_y = None
            for line in page.lines:
                # Add vertical spacing proportional to gap between lines
                if prev_y is not None:
                    gap = line.y0 - prev_y
                    if gap > 15:
                        story.append(Spacer(1, min(gap * 0.4, 20)))
                    elif gap > 6:
                        story.append(Spacer(1, 4))

                para = _line_to_paragraph(line, page.width)
                if para:
                    story.append(para)
                prev_y = line.y1

        elif page.raw_text:
            # Fallback: render raw text as paragraphs
            normal_style = styles["Normal"]
            for text_line in page.raw_text.split("\n"):
                if text_line.strip():
                    safe_text = text_line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    try:
                        story.append(Paragraph(safe_text, normal_style))
                    except Exception:
                        pass
                else:
                    story.append(Spacer(1, 6))

        # Append tables after page text
        if page.tables:
            story.append(Spacer(1, 12))
            for table_data in page.tables:
                tbl = _build_table_element(table_data)
                if tbl:
                    story.append(tbl)
                    story.append(Spacer(1, 8))

    if not story:
        story.append(Paragraph("No content extracted.", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()
