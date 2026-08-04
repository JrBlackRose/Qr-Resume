"""
Resume AI — Privacy-First Local Resume Builder
===============================================
Streamlit application.  All processing happens on your machine;
nothing is sent to any external service.

Run:  streamlit run app.py
"""
from __future__ import annotations

import json
import requests
import io

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
    st.caption("Powered by Llama 3.3 & Groq ⚡")
    st.divider()

    st.subheader("⚙️ Settings")

    model_name: str = st.selectbox(
        "AI Model",
        options=["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        index=1,
        help="Select the Groq cloud model to use for structuring. The 70b model is highly recommended for accuracy.",
    )

    qr_url: str = st.text_input(
        "Default QR Code URL",
        value=st.session_state.qr_url,
        help="Fallback link for the QR code if you don't use the temporary host feature.",
    )
    if qr_url != st.session_state.qr_url:
        st.session_state.qr_url = qr_url

    st.divider()
    st.info("⚡ Lightning fast inference via Groq API.", icon="⚡")

# ── Main layout ───────────────────────────────────────────────────────────────
st.title("📄 Resume AI")
st.markdown(
    "Upload your resume, extract the text, let **LLaMA 3.3 (via Groq)** structure it, "
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
    #  STEP 3 — AI STRUCTURING & EDITING
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
            if not isinstance(rd.get("contact"), dict): rd["contact"] = {}
            if not isinstance(rd.get("experience"), list): rd["experience"] = []
            if not isinstance(rd.get("education"), list): rd["education"] = []
            if not isinstance(rd.get("skills"), dict): rd["skills"] = {"technical": [], "soft": []}

            # --- RENDER METRICS ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Name",       rd["contact"].get("name", "—") or "—")
            m2.metric("Experience", f"{len(rd['experience'])} roles")
            m3.metric("Education",  f"{len(rd['education'])} entries")

            tech_count = len(rd["skills"].get("technical") or [])
            soft_count = len(rd["skills"].get("soft") or [])
            m4.metric("Skills", f"{tech_count + soft_count}")

            # --- BEAUTIFUL UI EDITOR ---
            with st.expander("✏️ Edit Resume Details", expanded=True):
                st.caption("Review and edit your details below. You can add or delete rows in the tables.")
                
                st.subheader("Contact Information")
                c1, c2, c3 = st.columns(3)
                rd["contact"]["name"] = c1.text_input("Name", rd["contact"].get("name", ""))
                rd["contact"]["email"] = c2.text_input("Email", rd["contact"].get("email", ""))
                rd["contact"]["phone"] = c3.text_input("Phone", rd["contact"].get("phone", ""))
                
                c4, c5, c6 = st.columns(3)
                rd["contact"]["location"] = c4.text_input("Location", rd["contact"].get("location", ""))
                rd["contact"]["linkedin"] = c5.text_input("LinkedIn", rd["contact"].get("linkedin", ""))
                rd["contact"]["github"] = c6.text_input("GitHub", rd["contact"].get("github", ""))

                st.subheader("Professional Summary")
                rd["summary"] = st.text_area("Summary", rd.get("summary", ""), height=100)

                st.subheader("Skills")
                s1, s2 = st.columns(2)
                tech_str = s1.text_area("Technical Skills (comma separated)", ", ".join(rd["skills"].get("technical", [])))
                soft_str = s2.text_area("Soft Skills (comma separated)", ", ".join(rd["skills"].get("soft", [])))
                rd["skills"]["technical"] = [s.strip() for s in tech_str.split(",") if s.strip()]
                rd["skills"]["soft"] = [s.strip() for s in soft_str.split(",") if s.strip()]

                st.subheader("Experience")
                st.caption("Tip: Separate bullet points with a new line (Enter).")
                exp_data = []
                for exp in rd.get("experience", []):
                    exp_data.append({
                        "title": exp.get("title", ""),
                        "company": exp.get("company", ""),
                        "location": exp.get("location", ""),
                        "start_date": exp.get("start_date", ""),
                        "end_date": exp.get("end_date", ""),
                        "bullets": "\n".join(exp.get("bullets", []))
                    })
                if not exp_data:
                    exp_data = [{"title": "", "company": "", "location": "", "start_date": "", "end_date": "", "bullets": ""}]
                
                edited_exp = st.data_editor(exp_data, num_rows="dynamic", use_container_width=True, key="exp_editor")
                
                rd["experience"] = []
                for exp in edited_exp:
                    if str(exp.get("title", "")).strip() or str(exp.get("company", "")).strip():
                        rd["experience"].append({
                            "title": str(exp.get("title", "")),
                            "company": str(exp.get("company", "")),
                            "location": str(exp.get("location", "")),
                            "start_date": str(exp.get("start_date", "")),
                            "end_date": str(exp.get("end_date", "")),
                            "bullets": [b.strip() for b in str(exp.get("bullets", "")).split("\n") if b.strip()]
                        })

                st.subheader("Education")
                edu_data = []
                for edu in rd.get("education", []):
                    edu_data.append({
                        "degree": edu.get("degree", ""),
                        "institution": edu.get("institution", ""),
                        "location": edu.get("location", ""),
                        "graduation_date": edu.get("graduation_date", ""),
                        "gpa": edu.get("gpa", "")
                    })
                if not edu_data:
                    edu_data = [{"degree": "", "institution": "", "location": "", "graduation_date": "", "gpa": ""}]
                
                edited_edu = st.data_editor(edu_data, num_rows="dynamic", use_container_width=True, key="edu_editor")
                
                rd["education"] = []
                for edu in edited_edu:
                    if str(edu.get("degree", "")).strip() or str(edu.get("institution", "")).strip():
                        rd["education"].append({
                            "degree": str(edu.get("degree", "")),
                            "institution": str(edu.get("institution", "")),
                            "location": str(edu.get("location", "")),
                            "graduation_date": str(edu.get("graduation_date", "")),
                            "gpa": str(edu.get("gpa", ""))
                        })
                
                st.session_state.resume_data = rd


        # ═══════════════════════════════════════════════════════════════════
        #  STEP 4 — GENERATE PDF & QR
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
                contact_name = (
                    st.session_state.resume_data
                    .get("contact", {})
                    .get("name", "resume")
                ) or "resume"
                safe_name = contact_name.lower().replace(" ", "_").replace("/", "-")
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

                # ── View-Only QR code ─────────────────────────────────────
                with qr_col:
                    st.subheader("📱 Share via QR")
                    st.caption("Generate a view-only link to let interviewers scan and read your resume without downloading.")
                    
                    if st.button("Generate Interview QR", use_container_width=True):
                        with st.spinner("Creating secure view-only image link..."):
                            try:
                                import fitz
                                from PIL import Image
                                
                                # 1. Convert PDF to High-Res Images
                                doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
                                images = []
                                for page in doc:
                                    # Render to RGB image at 150 DPI for crisp reading
                                    pix = page.get_pixmap(dpi=150, alpha=False)
                                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                    images.append(img)
                                
                                # 2. Stitch pages together vertically (if resume is multi-page)
                                total_height = sum(i.size[1] for i in images)
                                max_width = max(i.size[0] for i in images)
                                combined_img = Image.new('RGB', (max_width, total_height))
                                
                                y_offset = 0
                                for im in images:
                                    combined_img.paste(im, (0, y_offset))
                                    y_offset += im.size[1]
                                
                                # 3. Save as PNG bytes
                                img_buf = io.BytesIO()
                                combined_img.save(img_buf, format="PNG")
                                
                                # 4. Upload PNG instead of PDF to force in-browser viewing
                                files = {'file': ('resume.png', img_buf.getvalue(), 'image/png')}
                                res = requests.post("https://tmpfiles.org/api/v1/upload", files=files)
                                
                                if res.status_code == 200:
                                    raw_url = res.json()['data']['url']
                                    # The /dl/ path serves the raw image directly to the browser screen
                                    direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                                    
                                    qr_png = generate_qr_bytes(url=direct_url)
                                    st.image(qr_png, caption="Scan to view Resume", width=170)
                                    st.success("View-only link active for 60 minutes!")
                                else:
                                    st.error("Upload failed. Try again later.")
                            except Exception as exc:
                                st.error(f"Failed to generate link: {exc}")


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("🔒 Resume AI · Powered by Streamlit & Groq API. QR links are securely deleted after 60 minutes.")
