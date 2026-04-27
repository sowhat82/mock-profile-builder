"""
Mockify API — FastAPI backend for Vercel deployment (plain HTTP, no WebSockets).
"""
import base64
import os
import sys

# Ensure project root is on path so core/mocks/config modules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List

from core.extractor import extract
from core.detector import detect
from core.mapper import MappingTable
from core.anonymiser import anonymise_document
from core.generator import generate_pdf

app = FastAPI(title="Mockify API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pre-load spaCy model at module level so warm requests skip the cold-start penalty
try:
    import spacy as _spacy
    _nlp = _spacy.load("en_core_web_sm")
except Exception:
    _nlp = None


@app.post("/api/detect")
async def detect_pii(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        document = extract(pdf_bytes)
        detections = detect(document, use_spacy=True)

        mapping = MappingTable(scale_financials=False, financial_multiplier=1.0)
        mapping.build_from_detections(detections)
        records = mapping.to_records()

        return {
            "pdf_b64": base64.b64encode(pdf_bytes).decode(),
            "pii_items": [
                {
                    "pii_type": r["PII Type"],
                    "original": r["Original Value"],
                    "replacement": r["Proposed Replacement"],
                    "include": True,
                }
                for r in records
            ],
            "n_pages": len(document.pages),
            "n_pii": len(records),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PIIItem(BaseModel):
    pii_type: str
    original: str
    replacement: str
    include: bool = True


class GenerateRequest(BaseModel):
    pdf_b64: str
    pii_items: List[PIIItem]
    scale_financials: bool = False
    financial_multiplier: float = 1.0


@app.post("/api/generate")
async def generate_anonymised(req: GenerateRequest):
    try:
        pdf_bytes = base64.b64decode(req.pdf_b64)
        # Re-extract layout only (no ML detection — mapping already provided by client)
        document = extract(pdf_bytes)

        mapping = MappingTable(
            scale_financials=req.scale_financials,
            financial_multiplier=req.financial_multiplier,
        )
        for item in req.pii_items:
            if item.include:
                mapping.set_override(item.original, item.replacement)

        excluded = {item.original for item in req.pii_items if not item.include}
        anon_doc = anonymise_document(document, mapping, excluded)
        pdf_out = generate_pdf(anon_doc)

        return Response(
            content=pdf_out,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=anonymised_profile.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sample")
async def get_sample():
    sample_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "samples", "sample_client_profile.pdf",
    )
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample PDF not found")
    with open(sample_path, "rb") as f:
        data = f.read()
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=sample_client_profile.pdf"},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "spacy": _nlp is not None}
