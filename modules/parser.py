"""
Text extraction from uploaded resume files.
  - PDF  → PyMuPDF  (fitz)
  - Image → RapidOCR (rapidocr-onnxruntime)
"""
from __future__ import annotations

import io


# ── PDF extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF using PyMuPDF.

    Iterates every page and concatenates the plain-text layer.
    Works well for text-based PDFs; for fully scanned PDFs, use
    extract_text_from_image() after rasterising the pages.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF is required: pip install PyMuPDF"
        ) from exc

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages).strip()


# ── Image extraction ─────────────────────────────────────────────────────────

def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Run OCR on an image using RapidOCR.

    RapidOCR is a pure-Python, ONNX-based OCR engine — no internet,
    no Tesseract, no CUDA required.  Each result item is a tuple of
    (bounding-box, text, confidence).
    """
    try:
        import numpy as np
        from PIL import Image
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise ImportError(
            "OCR deps required: pip install rapidocr-onnxruntime pillow numpy"
        ) from exc

    engine = RapidOCR()
    pil_img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img_array = np.array(pil_img)

    result, _ = engine(img_array)

    if not result:
        return ""

    # result[i] = [bounding_box, text, confidence]
    lines = [item[1] for item in result if item[1]]
    return "\n".join(lines).strip()


# ── Public dispatcher ────────────────────────────────────────────────────────

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Auto-detect file type and dispatch to the correct extractor.

    Args:
        file_bytes: Raw file bytes from st.file_uploader.
        filename:   Original filename (used for extension sniffing).

    Returns:
        Plain-text content of the resume.

    Raises:
        ValueError:    Unsupported file extension.
        RuntimeError:  Extraction produced no text (e.g. blank PDF).
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        text = extract_text_from_pdf(file_bytes)
    elif ext in _IMAGE_EXTS:
        text = extract_text_from_image(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Please upload a PDF or image ({', '.join(sorted(_IMAGE_EXTS))})."
        )

    if not text:
        raise RuntimeError(
            "No text could be extracted from the file.  "
            "If it is a scanned PDF, please export individual page images and try again."
        )

    return text
