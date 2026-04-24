"""
Generates a simple pseudo client profile PDF for testing.
Run: python samples/generate_sample.py
"""
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_LEFT
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "sample_client_profile.pdf")

SOW_PARAGRAPH = (
    "Mr Bernard Tan Wei Jian accumulated his wealth primarily through the founding and "
    "subsequent sale of CapVista Technologies Pte Ltd, a Singapore-based enterprise software "
    "company specialising in treasury management systems for regional banks. Established in 2004, "
    "CapVista grew to serve over 40 financial institutions across Southeast Asia before being "
    "acquired by a US-listed fintech group in 2019 for an undisclosed sum reported to be in "
    "excess of S$85 million. Mr Tan retained a 62% equity stake at the time of exit. "
    "Prior to founding CapVista, he held senior technology roles at DBS Bank and Standard "
    "Chartered, where he accumulated domain expertise in core banking infrastructure. "
    "A secondary source of wealth derives from a portfolio of commercial real estate holdings "
    "in Singapore and Kuala Lumpur, acquired progressively between 2010 and 2018, with an "
    "estimated combined value of S$12 million. Mr Tan has no outstanding litigation, "
    "bankruptcy proceedings, or adverse regulatory history on record."
)


def generate():
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    w, h = A4

    def text(content, y, size=11, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(50, y, content)

    def wrapped_paragraph(content, y_start, font_size=10.5, max_width=495, line_height=16):
        """Draw word-wrapped text, returns the y position after the last line."""
        c.setFont("Helvetica", font_size)
        words = content.split()
        lines = []
        current = []
        for word in words:
            test_line = " ".join(current + [word])
            if c.stringWidth(test_line, "Helvetica", font_size) <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))

        y = y_start
        for ln in lines:
            c.drawString(50, y, ln)
            y -= line_height
        return y

    # Header
    text("CLIENT PROFILE", h - 60, size=16, bold=True)
    c.setFont("Helvetica", 8)
    c.drawString(50, h - 73, "─" * 100)

    # Basic fields
    text("Name:", h - 100, bold=True)
    text("Bernard Tan Wei Jian", h - 114)

    text("Address:", h - 138, bold=True)
    text("14 Ridgewood Close, #04-02, Singapore 276888", h - 152)

    text("Company:", h - 176, bold=True)
    text("CapVista Technologies Pte Ltd", h - 190)

    # Divider
    c.setFont("Helvetica", 8)
    c.drawString(50, h - 210, "─" * 100)

    # Source of wealth section
    text("Source of Wealth", h - 230, size=12, bold=True)
    wrapped_paragraph(SOW_PARAGRAPH, h - 252)

    c.save()
    print(f"Sample PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
