"""
Resume AI — Privacy-First Local Resume Builder
===============================================
Streamlit application.  All processing happens on your machine;
nothing is sent to any external service.

Run:  streamlit run app.py
"""
from __future__ import annotations

import json

import streamlit as st

from modules import extract_text, structure_resume, generate_pdf, generate_qr_bytes


# ── Page configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Slightly wider sidebar */
    section[data-testid="stSidebar"] { min-width: 280px; }

    /* Step header styling */
    h2 { border-left: 4px solid #2c5f8a; padding-left: 0.5rem; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #f0f4f8;
        border-radius: 8px;
        padding: 0.6rem 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Session state initialisation ─────────────────────────────────────────────
_DEFAULTS: dict = {
    "last_filename":  None,
    "raw_text":       None,
    "resume_data":    None,
    "pdf_bytes":      None,
    "qr_url":         "https://metaresume.streamlit.app",
}
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📄 Resume AI")
    st.caption("Powered by Llama 3.1 & Groq ⚡")
    st.divider()

    st.subheader("⚙️ Settings")

    model_name: str = st.selectbox(
        "AI Model",
        options=["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
        index=0,
        help="Select the Groq cloud model to use for structuring.",
    )

    qr_url: str = st.text_input(
        "QR Code URL",
        value=st.session_state.qr_url,
        help="The link that the generated QR code will point to.",
    )
    if qr_url != st.session_state.qr_url:
        st.session_state.qr_url = qr_url

    st.divider()
    st.info("⚡ Lightning fast inference via Groq API.", icon="⚡")

# ── Main layout ───────────────────────────────────────────────────────────────
st.title("📄 Resume AI")
st.markdown(
    "Upload your resume, extract the text, let **LLaMA 3.1 (via Groq)** structure it, "
    "and export a polished ATS-friendly PDF instantly."
)
st.divider()


# ═════════════════════════════════════════════════════════════════════════════
#  STEP 1 — UPLOAD
# ═════════════════════════════════════════════════════════════════════════════
st.header("① Upload Resume")

uploaded_file = st.file_uploader(
    "Drop your resume here",
    type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"],
    label_visibility="collapsed",
    help="PDF for text-based resumes; image formats trigger OCR.",
)

if uploaded_file is not None:
    # Reset pipeline when a new file is uploaded
    if st.session_state.last_filename != uploaded_file.name:
        st.session_state.last_filename = uploaded_file.name
        st.session_state.raw_text    = None
        st.session_state.resume_data = None
        st.session_state.pdf_bytes   = None

    with st.expander(f"📎 {uploaded_file.name}  —  {uploaded_file.size / 1024:.1f} KB"):
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("File name", uploaded_file.name)
        col_b.metric("Size",      f"{uploaded_file.size / 1024:.1f} KB")
        col_c.metric("Type",      uploaded_file.type or "unknown")


    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 2 — EXTRACT TEXT
    # ═══════════════════════════════════════════════════════════════════════
    st.header("② Extract Text")

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        do_extract = st.button(
            "🔍 Extract Text",
            use_container_width=True,
            type="primary",
            disabled=(st.session_state.raw_text is not None),
        )

    if do_extract:
        with st.spinner("Extracting text…  (OCR may take 10–20 s for images)"):
            try:
                file_bytes = uploaded_file.read()
                st.session_state.raw_text = extract_text(file_bytes, uploaded_file.name)
                st.success("✅ Text extracted successfully!")
            except Exception as exc:
                st.error(f"❌ Extraction failed: {exc}")
                st.session_state.raw_text = None

    if st.session_state.raw_text:
        char_count = len(st.session_state.raw_text)
        st.caption(f"Extracted {char_count:,} characters.")
        with st.expander("📝 View raw extracted text"):
            st.text_area(
                "raw",
                value=st.session_state.raw_text,
                height=220,
                label_visibility="collapsed",
                disabled=True,
            )


    # ═══════════════════════════════════════════════════════════════════════
    #  STEP 3 — AI STRUCTURING
    # ═══════════════════════════════════════════════════════════════════════
    if st.session_state.raw_text:
        st.header("③ Structure with AI")

        col_btn2, _ = st.columns([1, 4])
        with col_btn2:
            do_ai = st.button(
                f"🤖 Structure with {model_name}",
                use_container_width=True,
                type="primary",
                disabled=(st.session_state.resume_data is not None),
            )

        if do_ai:
            with st.spinner(f"Sending to {model_name} via Groq API…"):
                try:
                    st.session_state.resume_data = structure_resume(
                        st.session_state.raw_text,
                        model=model_name,
                    )
                    st.session_state.pdf_bytes = None
                    st.success("✅ Resume structured successfully!")
                except Exception as exc:
                    st.error(f"❌ AI structuring failed: {exc}")
                    st.info("Make sure your GROQ_API_KEY is correctly set in Streamlit Secrets.")
                    st.session_state.resume_data = None

    if st.session_state.resume_data:
            rd = st.session_state.resume_data
        
            # --- DEFENSIVE SANITIZATION ---
            # Force lazy LLM outputs into the correct data types
            if not isinstance(rd.get("contact"), dict): rd["contact"] = {}
            if not isinstance(rd.get("experience"), list): rd["experience"] = []
            if not isinstance(rd.get("education"), list): rd["education"] = []
            if not isinstance(rd.get("skills"), dict): rd["skills"] = {"technical": [], "soft": []}
        
            # --- RENDER METRICS ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Name",       rd["contact"].get("name", "—") or "—")
            m2.metric("Experience", f"{len(rd['experience'])} roles")
            m3.metric("Education",  f"{len(rd['education'])} entries")
        
            # Safely count skills even if the AI returned nulls inside the dict
            tech_count = len(rd["skills"].get("technical") or [])
            soft_count = len(rd["skills"].get("soft") or [])
            m4.metric("Skills", f"{tech_count + soft_count}")

        # ═══════════════════════════════════════════════════════════════════
        #  STEP 4 — GENERATE PDF
        # ═══════════════════════════════════════════════════════════════════
        if st.session_state.resume_data:
            st.header("④ Generate ATS-Friendly PDF")

            col_btn3, _ = st.columns([1, 4])
            with col_btn3:
                do_pdf = st.button(
                    "📄 Generate PDF",
                    use_container_width=True,
                    type="primary",
                )

            if do_pdf:
                with st.spinner("Compiling Typst template…"):
                    try:
                        st.session_state.pdf_bytes = generate_pdf(st.session_state.resume_data)
                        st.success("✅ PDF generated!")
                    except Exception as exc:
                        st.error(f"❌ PDF generation failed:\n\n{exc}")
                        st.session_state.pdf_bytes = None

            if st.session_state.pdf_bytes:
                # Build a clean filename
                contact_name = (
                    st.session_state.resume_data
                    .get("contact", {})
                    .get("name", "resume")
                ) or "resume"
                safe_name = (
                    contact_name
                    .lower()
                    .replace(" ", "_")
                    .replace("/", "-")
                )
                pdf_filename = f"{safe_name}_resume.pdf"

                pdf_col, qr_col = st.columns([3, 1])

                # ── Download button ───────────────────────────────────────
                with pdf_col:
                    st.subheader("⬇️ Download")
                    st.download_button(
                        label="Download PDF",
                        data=st.session_state.pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
                    pdf_kb = len(st.session_state.pdf_bytes) / 1024
                    st.caption(
                        f"**{pdf_filename}**  ·  {pdf_kb:.1f} KB  ·  "
                        "Typst-compiled, searchable, ATS-safe"
                    )

                # ── QR code ───────────────────────────────────────────────
                with qr_col:
                    st.subheader("📱 Share via QR")
                    try:
                        qr_png = generate_qr_bytes(url=st.session_state.qr_url)
                        st.image(qr_png, caption=st.session_state.qr_url, width=170)
                        st.download_button(
                            label="Save QR PNG",
                            data=qr_png,
                            file_name="resume_qr.png",
                            mime="image/png",
                            use_container_width=True,
                        )
                    except Exception as exc:
                        st.warning(f"QR generation failed: {exc}")


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("🔒 Resume AI · Powered by Streamlit & Groq API.")
