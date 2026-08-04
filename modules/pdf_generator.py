"""
PDF generation via the Typst typesetting system.

Workflow:
  1. Create an isolated temp directory.
  2. Copy template.typ into it.
  3. Serialise the resume dict to resume_data.json alongside the template
     (Typst reads it with  #let data = json("resume_data.json")).
  4. Compile with the `typst` Python package (Rust bindings).
     Falls back to the `typst` CLI via subprocess if the package is absent.
  5. Return raw PDF bytes; caller decides what to do with them.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

# Template lives next to this package's parent directory
_TEMPLATE_PATH = Path(__file__).parent.parent / "template.typ"


# ── Compilation strategies ────────────────────────────────────────────────────

def _compile_with_package(typ_file: Path, root_dir: Path) -> bytes:
    """Use the `typst` Python package (preferred)."""
    import typst  # type: ignore[import]
    return typst.compile(str(typ_file), root=str(root_dir))


def _compile_with_cli(typ_file: Path, out_pdf: Path, root_dir: Path) -> bytes:
    """Fallback: invoke the `typst` CLI binary via subprocess."""
    cmd = [
        "typst", "compile",
        "--root", str(root_dir),
        str(typ_file),
        str(out_pdf),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Typst CLI compilation failed (exit {proc.returncode}):\n"
            f"{proc.stderr or proc.stdout}"
        )
    return out_pdf.read_bytes()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(
    resume_data: dict,
    template_path: Path | None = None,
) -> bytes:
    """
    Render a Typst resume template with the provided structured data.

    Args:
        resume_data:   Structured resume dict produced by ai_structurer.
        template_path: Optional override for template.typ location.

    Returns:
        Raw PDF bytes ready for download or further processing.

    Raises:
        FileNotFoundError: template.typ is missing.
        RuntimeError:      Typst compilation failed.
        ImportError:       Neither typst package nor typst CLI is available.
    """
    tpl = template_path or _TEMPLATE_PATH
    if not tpl.exists():
        raise FileNotFoundError(
            f"Typst template not found at: {tpl}\n"
            "Make sure template.typ is in the project root."
        )

    with tempfile.TemporaryDirectory(prefix="resume_ai_") as tmp_str:
        tmp = Path(tmp_str)

        # Place template and data in the same directory so
        # json("resume_data.json") resolves correctly in Typst.
        tmp_tpl = tmp / "template.typ"
        shutil.copy(tpl, tmp_tpl)

        data_file = tmp / "resume_data.json"
        data_file.write_text(
            json.dumps(resume_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Try Python package first, then CLI binary
        try:
            return _compile_with_package(tmp_tpl, tmp)
        except ImportError:
            pass  # package not installed — try CLI

        # Check for CLI binary
        if shutil.which("typst") is None:
            raise ImportError(
                "Neither the `typst` Python package nor the `typst` CLI binary "
                "is available.\n"
                "Install with:  pip install typst\n"
                "  or visit:    https://github.com/typst/typst/releases"
            )

        out_pdf = tmp / "output.pdf"
        return _compile_with_cli(tmp_tpl, out_pdf, tmp)
