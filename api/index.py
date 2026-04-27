"""
Mockify API — Flask backend for Vercel deployment (WSGI, plain HTTP).
"""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, make_response

from core.extractor import extract
from core.detector import detect
from core.mapper import MappingTable
from core.anonymiser import anonymise_document
from core.generator import generate_pdf

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

# Pre-load spaCy at module level so warm requests skip the cold-start penalty
try:
    import spacy as _spacy
    _nlp = _spacy.load("en_core_web_sm")
except Exception:
    _nlp = None


@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/api/detect", methods=["POST", "OPTIONS"])
def detect_pii():
    if request.method == "OPTIONS":
        return "", 204
    try:
        f = request.files.get("file")
        if not f:
            return jsonify({"detail": "No file provided"}), 400
        pdf_bytes = f.read()
        document = extract(pdf_bytes)
        detections = detect(document, use_spacy=True)
        mapping = MappingTable(scale_financials=False, financial_multiplier=1.0)
        mapping.build_from_detections(detections)
        records = mapping.to_records()
        return jsonify({
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
        })
    except Exception as e:
        return jsonify({"detail": str(e)}), 500


@app.route("/api/generate", methods=["POST", "OPTIONS"])
def generate_anonymised():
    if request.method == "OPTIONS":
        return "", 204
    try:
        data = request.get_json(force=True)
        pdf_bytes = base64.b64decode(data["pdf_b64"])
        pii_items = data["pii_items"]
        document = extract(pdf_bytes)
        mapping = MappingTable(
            scale_financials=bool(data.get("scale_financials", False)),
            financial_multiplier=float(data.get("financial_multiplier", 1.0)),
        )
        for item in pii_items:
            if item.get("include", True):
                mapping.set_override(item["original"], item["replacement"])
        excluded = {item["original"] for item in pii_items if not item.get("include", True)}
        anon_doc = anonymise_document(document, mapping, excluded)
        pdf_out = generate_pdf(anon_doc)
        resp = make_response(pdf_out)
        resp.headers["Content-Type"] = "application/pdf"
        resp.headers["Content-Disposition"] = "attachment; filename=anonymised_profile.pdf"
        return resp
    except Exception as e:
        return jsonify({"detail": str(e)}), 500


@app.route("/api/sample")
def get_sample():
    sample_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "samples", "sample_client_profile.pdf",
    )
    if not os.path.exists(sample_path):
        return jsonify({"detail": "Sample not found"}), 404
    with open(sample_path, "rb") as f:
        data = f.read()
    resp = make_response(data)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = "inline; filename=sample_client_profile.pdf"
    return resp


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "spacy": _nlp is not None})
