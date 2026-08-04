"""
QR code generation using the `qrcode` library (PIL backend).

Produces a PNG image (as bytes) that encodes a URL — typically a
Cloudflare Tunnel URL or the local Streamlit address — so a phone
can scan it and pull down the generated PDF directly.
"""
from __future__ import annotations

import io

import qrcode
import qrcode.constants


DEFAULT_URL = "http://localhost:8501"


def generate_qr_bytes(
    url: str = DEFAULT_URL,
    *,
    fill_color: str = "#1b2a4a",   # matches navy in template.typ
    back_color: str = "#ffffff",
    box_size: int = 8,
    border: int = 2,
) -> bytes:
    """
    Generate a QR code PNG and return it as raw bytes.

    Args:
        url:        The URL to encode.  Set this to your Cloudflare Tunnel
                    URL (e.g. https://my-resume.trycloudflare.com/download)
                    or leave as the localhost default for purely local use.
        fill_color: Hex colour for the dark QR modules.
        back_color: Hex colour for the background.
        box_size:   Pixel width/height of each QR module square.
        border:     Quiet-zone size in modules (QR spec minimum is 4).

    Returns:
        PNG image as bytes, ready for st.image() or st.download_button().
    """
    qr = qrcode.QRCode(
        version=None,                              # auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% damage tolerance
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
