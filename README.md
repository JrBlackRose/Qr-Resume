# Resume AI — Privacy-First Local Resume Builder

Build a polished, ATS-friendly PDF from any resume — entirely on your machine.

```
Upload PDF/image → Extract text → LLaMA 3.1 structures it → Typst renders PDF → QR to share
```

No data ever leaves your computer.

---

## Stack

| Layer | Library | Purpose |
|---|---|---|
| Frontend | `streamlit` | Web UI |
| PDF parsing | `PyMuPDF` (fitz) | Text extraction from PDF |
| Image OCR | `rapidocr-onnxruntime` | Text extraction from image resumes |
| AI | `ollama` + `llama3.1` | JSON-structured resume extraction |
| PDF generation | `typst` | Typesetting the final PDF |
| QR code | `qrcode` + `Pillow` | Shareable QR for the download link |

---

## Quick Start

### 1 — Install Ollama and pull the model

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1          # ~4.7 GB for the 8B model

# Windows: download from https://ollama.com
```

### 2 — Create a virtual environment and install Python deps

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3 — Run

```bash
# In one terminal — keep Ollama running:
ollama serve

# In another terminal:
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Cloudflare Tunnel (optional — share with others)

```bash
# Install cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

cloudflared tunnel --url http://localhost:8501
# → outputs: https://random-name.trycloudflare.com
```

Paste that URL into the **QR Code URL** field in the sidebar.  
The generated QR code will now point to your public tunnel, so anyone can
scan it to download your resume.

---

## Project Layout

```
resume_ai/
├── app.py                  Main Streamlit application
├── template.typ            Typst resume template (edit to customise layout)
├── requirements.txt
├── README.md
└── modules/
    ├── __init__.py
    ├── parser.py           PDF & image text extraction
    ├── ai_structurer.py    Ollama/LLaMA JSON structuring
    ├── pdf_generator.py    Typst compilation → PDF bytes
    └── qr_generator.py     QR code PNG generation
```

---

## Customising the Template

`template.typ` is a standard Typst source file.  Edit colours, fonts, spacing,
or layout freely.  The only contract it must honour is reading:

```typst
#let data = json("resume_data.json")
```

where `resume_data.json` has the structure emitted by `ai_structurer.py`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ollama: connection refused` | Run `ollama serve` in a separate terminal |
| `model not found` | Run `ollama pull llama3.1` |
| `typst: command not found` | `pip install typst` (Python package bundles the compiler) |
| Image OCR returns empty string | Ensure the image is sharp and high-contrast |
| JSON parse error in AI step | Try a larger model (`llama3.1:70b`) or edit the JSON manually |
