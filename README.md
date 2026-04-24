# Mock Profile Builder

Prototype web app that takes a real client PDF profile and outputs a fully anonymised/mocked version for use as test data in wealth management systems.

## Quick start

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
streamlit run app.py
```

## What it does

1. Upload a client profile PDF
2. Detects PII using regex patterns + spaCy NER
3. Replaces all PII with realistic fake equivalents (consistent: same original → same replacement throughout)
4. Generates a downloadable anonymised PDF

## PII types detected

| Type | Example |
|------|---------|
| Names | `John Tan` → `Wei Ming Lim-test-data` |
| Emails | `john.tan@bank.com` → `wei.ming-test-data@example.com` |
| NRIC / FIN | `S1234567A` → `T9876543B` (valid check digit) |
| Phone (SG) | `+65 9123 4567` → `+65 8745 2391` |
| Dates | `15/06/1975` → `15/06/1972` (shifted ±3–7 years) |
| Addresses | `123 Orchard Rd, Singapore 238801` → fake SG address |
| Financial figures | `S$2,500,000` → `S$3,750,000` (if scaling enabled) |
| Companies | `ABC Capital Pte Ltd` → `Financial Holdings Test-Data Pte Ltd` |
| Account numbers | `P-123456789` → `P-530061661` (same format) |
| Passports | `E1234567A` → `E9283741K` |

## Project structure

```
app.py              # Streamlit UI
config/
  patterns.py       # Regex patterns (SG-focused)
core/
  extractor.py      # PDF text + layout extraction (pdfplumber)
  detector.py       # PII detection: regex + spaCy NER
  mapper.py         # Consistent original → fake mapping table
  anonymiser.py     # Applies mapping to text
  generator.py      # Builds output PDF (reportlab)
mocks/
  names.py          # Name faker (cultural style aware)
  addresses.py      # Address faker (same country)
  phones.py         # Phone number faker (country-code aware)
  ids.py            # NRIC / passport / account number faker
  financials.py     # Financial figure scaling
  entities.py       # Company name faker
```

## Notes

- Optimised for Singapore wealth management profiles (NRIC, SGD amounts, SG phone numbers, SG addresses)
- spaCy `en_core_web_sm` handles name and organisation entity recognition
- PDF layout is reconstructed as a "structured approximation" — not pixel-perfect
- All replacements are consistent within a session: the same original value always maps to the same fake value
