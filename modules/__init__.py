"""
Resume AI — local processing modules.
"""
from .parser import extract_text
from .ai_structurer import structure_resume
from .pdf_generator import generate_pdf
from .qr_generator import generate_qr_bytes

__all__ = ["extract_text", "structure_resume", "generate_pdf", "generate_qr_bytes"]
