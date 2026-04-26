"""
Mock Profile Builder — Streamlit UI
Anonymises client PDF profiles for use as test data in wealth management systems.
"""
import io
import os
import re
import streamlit as st
import pandas as pd

from core.extractor import extract, DocumentContent
from core.detector import detect, PIIDetection, spacy_status
from core.mapper import MappingTable
from core.anonymiser import anonymise_document
from core.generator import generate_pdf

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Mock Profile Builder",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔒 Mock Profile Builder")
st.caption("Upload a client PDF profile and generate a fully anonymised version for test data.")

# ─── Session state initialisation ─────────────────────────────────────────────

def _init_state():
    defaults = {
        "document": None,
        "detections": None,
        "mapping_table": None,
        "output_pdf_bytes": None,
        "scale_financials": False,
        "financial_multiplier": 1.0,
        "pii_df": None,
        "excluded_originals": set(),
        "upload_key": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        key=f"uploader_{st.session_state.upload_key}",
        help="Upload a client profile PDF to anonymise",
    )

    # spaCy NER status
    _spacy_ok, _spacy_err = spacy_status()
    if _spacy_ok:
        st.success("NER: spaCy loaded ✓", icon="🧠")
    else:
        st.error(f"NER unavailable — name/company detection disabled. {_spacy_err}", icon="⚠️")

    st.caption("— or —")
    if st.button("📄 Load sample document", use_container_width=True,
                 help="Load a pre-built pseudo client profile (Bernard Tan, Meridian Private Bank)"):
        sample_path = os.path.join(os.path.dirname(__file__), "samples", "sample_client_profile.pdf")
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                st.session_state["_sample_pdf_bytes"] = f.read()
                st.session_state["_use_sample"] = True
        else:
            st.error("Sample PDF not found. Run: python samples/generate_sample.py")

    st.divider()

    scale_toggle = st.toggle(
        "Scale financial figures",
        value=st.session_state.scale_financials,
        help="Multiply all financial amounts by a random factor (0.5×–2×) to obscure original values",
    )

    multiplier_val = st.session_state.financial_multiplier
    if scale_toggle:
        multiplier_val = st.slider(
            "Scale multiplier",
            min_value=0.5,
            max_value=2.0,
            value=float(st.session_state.financial_multiplier),
            step=0.05,
            format="%.2f×",
        )

    # Detect changes to financial settings
    if (scale_toggle != st.session_state.scale_financials or
            multiplier_val != st.session_state.financial_multiplier):
        st.session_state.scale_financials = scale_toggle
        st.session_state.financial_multiplier = multiplier_val
        if st.session_state.mapping_table:
            st.session_state.mapping_table.scale_financials = scale_toggle
            st.session_state.mapping_table.multiplier = multiplier_val
            # Refresh the PII dataframe
            if st.session_state.mapping_table:
                records = st.session_state.mapping_table.to_records()
                st.session_state.pii_df = pd.DataFrame(records)
        st.session_state.output_pdf_bytes = None

    st.divider()

    # Resolve active PDF source (upload or sample)
    _sample_bytes = st.session_state.get("_sample_pdf_bytes")
    _active_pdf = uploaded_file is not None or bool(_sample_bytes)

    if _active_pdf:
        if st.button("🔍 Detect PII", type="primary", use_container_width=True):
            with st.spinner("Extracting text and detecting PII…"):
                if _sample_bytes:
                    pdf_bytes = _sample_bytes
                else:
                    pdf_bytes = uploaded_file.read()
                try:
                    document = extract(pdf_bytes)
                    st.session_state.document = document

                    detections = detect(document, use_spacy=True)
                    st.session_state.detections = detections

                    mapping_table = MappingTable(
                        scale_financials=st.session_state.scale_financials,
                        financial_multiplier=st.session_state.financial_multiplier,
                    )
                    mapping_table.build_from_detections(detections)
                    st.session_state.mapping_table = mapping_table

                    records = mapping_table.to_records()
                    st.session_state.pii_df = pd.DataFrame(records) if records else pd.DataFrame(
                        columns=["PII Type", "Original Value", "Proposed Replacement", "Include"]
                    )
                    st.session_state.output_pdf_bytes = None
                    st.session_state.excluded_originals = set()

                    n_pages = len(document.pages)
                    n_pii = len(detections)
                    st.success(f"Found {n_pii} PII items across {n_pages} page(s)")
                except Exception as e:
                    st.error(f"Error processing PDF: {e}")

        st.divider()

        if st.session_state.mapping_table and st.session_state.document:
            if st.button("⚙️ Generate Anonymised PDF", use_container_width=True):
                with st.spinner("Anonymising and generating PDF…"):
                    try:
                        # Apply any user edits from the PII table
                        if st.session_state.pii_df is not None:
                            df = st.session_state.pii_df
                            excluded = set(
                                df.loc[~df["Include"], "Original Value"].tolist()
                            )
                            overrides = dict(zip(df["Original Value"], df["Proposed Replacement"]))
                            st.session_state.mapping_table.apply_overrides(overrides)
                            st.session_state.excluded_originals = excluded

                        anon_doc = anonymise_document(
                            st.session_state.document,
                            st.session_state.mapping_table,
                            st.session_state.excluded_originals,
                        )
                        pdf_bytes = generate_pdf(anon_doc)
                        st.session_state.output_pdf_bytes = pdf_bytes
                        st.success("PDF generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating PDF: {e}")
                        st.exception(e)

    if st.button("🔄 Reset", use_container_width=True):
        for k in ["document", "detections", "mapping_table", "output_pdf_bytes",
                  "pii_df", "excluded_originals"]:
            st.session_state[k] = None if k != "excluded_originals" else set()
        st.session_state.pop("_sample_pdf_bytes", None)
        st.session_state.pop("_use_sample", None)
        st.session_state.upload_key += 1
        st.rerun()

# ─── Main content area ────────────────────────────────────────────────────────

if st.session_state.document is None:
    st.info("👈 Upload a PDF **or** click **Load sample document** in the sidebar, then click **Detect PII** to get started.")
    st.markdown("""
    **What this tool does:**
    - Extracts all text from your PDF
    - Detects PII: names, emails, phone numbers, NRIC/passport numbers, addresses, financial figures, and more
    - Replaces each with a realistic but fake equivalent (consistently — same original → same replacement)
    - Generates a downloadable anonymised PDF

    **Supported PII types (Singapore wealth management focus):**
    | Type | Example |
    |------|---------|
    | Names | `John Tan` → `Wei Ming Lim-test-data` |
    | Emails | `john.tan@bank.com` → `wei.ming-test-data@example.com` |
    | NRIC/FIN | `S1234567A` → `T9876543B` |
    | Phone (SG) | `+65 9123 4567` → `+65 8745 2391` |
    | Dates | `01/01/1980` → `01/01/1975` |
    | Addresses | `123 Orchard Rd, Singapore 238801` → `45 Tampines Ave, #12-08, Singapore 521045` |
    | Financial | `S$1,500,000` → `S$2,175,000` (if scaling enabled) |
    | Companies | `ABC Capital Pte Ltd` → `Financial Holdings Test-Data Pte Ltd` |
    """)

else:
    tabs = st.tabs(["📋 PII Review & Edit", "📄 Text Preview", "⬇️ Download"])

    # ── Tab 1: PII Review ────────────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Detected PII Items")
        st.caption("Review and edit proposed replacements. Uncheck items to exclude them from anonymisation.")

        if st.session_state.pii_df is not None and not st.session_state.pii_df.empty:
            # Filter controls
            col1, col2 = st.columns([2, 1])
            with col1:
                pii_types = ["All"] + sorted(st.session_state.pii_df["PII Type"].unique().tolist())
                filter_type = st.selectbox("Filter by PII type", pii_types, key="filter_type")
            with col2:
                search_term = st.text_input("Search original values", key="search_term", placeholder="e.g. John")

            display_df = st.session_state.pii_df.copy()
            if filter_type != "All":
                display_df = display_df[display_df["PII Type"] == filter_type]
            if search_term:
                mask = display_df["Original Value"].str.contains(search_term, case=False, na=False)
                display_df = display_df[mask]

            edited_df = st.data_editor(
                display_df,
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "PII Type": st.column_config.TextColumn("PII Type", disabled=True, width="small"),
                    "Original Value": st.column_config.TextColumn("Original Value", disabled=True, width="medium"),
                    "Proposed Replacement": st.column_config.TextColumn("Proposed Replacement", width="large"),
                    "Include": st.column_config.CheckboxColumn("Include", width="small"),
                },
                hide_index=True,
                key="pii_editor",
            )

            # Merge edits back into the full dataframe
            if filter_type != "All" or search_term:
                for idx, row in edited_df.iterrows():
                    mask = st.session_state.pii_df["Original Value"] == row["Original Value"]
                    st.session_state.pii_df.loc[mask, "Proposed Replacement"] = row["Proposed Replacement"]
                    st.session_state.pii_df.loc[mask, "Include"] = row["Include"]
            else:
                st.session_state.pii_df = edited_df

            n_included = int(st.session_state.pii_df["Include"].sum())
            n_total = len(st.session_state.pii_df)
            st.caption(f"**{n_included}** of **{n_total}** items will be anonymised.")

        else:
            st.warning("No PII items detected. The document may not contain recognisable PII, or text extraction may have failed.")

    # ── Tab 2: Text Preview ──────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Extracted Text Preview")
        st.caption("Preview of the extracted text per page (before anonymisation).")

        n_pages = len(st.session_state.document.pages)
        if n_pages > 1:
            page_idx = st.selectbox(
                "Select page",
                range(n_pages),
                format_func=lambda i: f"Page {i + 1}",
                key="preview_page",
            )
        else:
            page_idx = 0

        page = st.session_state.document.pages[page_idx]

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("**Original text:**")
            st.text_area(
                "original_text",
                value=page.raw_text or "(No text extracted)",
                height=400,
                label_visibility="collapsed",
                key="orig_preview",
            )
        with col_right:
            st.markdown("**Anonymised preview:**")
            if st.session_state.mapping_table:
                from core.anonymiser import anonymise_text
                excluded = set()
                if st.session_state.pii_df is not None:
                    excluded = set(
                        st.session_state.pii_df.loc[
                            ~st.session_state.pii_df["Include"], "Original Value"
                        ].tolist()
                    )
                # Apply edits before preview
                if st.session_state.pii_df is not None:
                    overrides = dict(zip(
                        st.session_state.pii_df["Original Value"],
                        st.session_state.pii_df["Proposed Replacement"]
                    ))
                    st.session_state.mapping_table.apply_overrides(overrides)

                anon_text = anonymise_text(page.raw_text or "", st.session_state.mapping_table, excluded)
                st.text_area(
                    "anon_text",
                    value=anon_text or "(No text)",
                    height=400,
                    label_visibility="collapsed",
                    key="anon_preview",
                )
            else:
                st.info("Run PII detection first.")

    # ── Tab 3: Download ──────────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Download Anonymised PDF")

        if st.session_state.output_pdf_bytes:
            n_replaced = len(st.session_state.mapping_table) if st.session_state.mapping_table else 0
            n_pages = len(st.session_state.document.pages) if st.session_state.document else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("Pages processed", n_pages)
            col2.metric("PII items replaced", n_replaced)
            col3.metric("Output size", f"{len(st.session_state.output_pdf_bytes) / 1024:.1f} KB")

            st.download_button(
                label="⬇️ Download Anonymised PDF",
                data=st.session_state.output_pdf_bytes,
                file_name="anonymised_profile.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

            if st.session_state.scale_financials:
                st.info(f"Financial figures were scaled by **{st.session_state.financial_multiplier:.2f}×**")

        else:
            st.info("👈 Click **Generate Anonymised PDF** in the sidebar after reviewing the PII items.")

            if st.session_state.mapping_table:
                st.markdown("**Steps to generate:**")
                st.markdown("1. Review and edit PII replacements in the **PII Review** tab")
                st.markdown("2. Optionally enable financial figure scaling in the sidebar")
                st.markdown("3. Click **Generate Anonymised PDF** in the sidebar")
