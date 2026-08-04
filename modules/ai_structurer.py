"""
Resume structuring via the Groq API (Cloud).
Runs Llama 3.1 instantly and for free, with no local GPU required.
"""
from __future__ import annotations
import json
import re
import os
import streamlit as st
from groq import Groq

# ── Prompt ───────────────────────────────────────────────────────────────────
# (Keep your exact _SYSTEM_PROMPT and _USER_TEMPLATE from the previous code here)
_SYSTEM_PROMPT = """...""" # Paste the same prompt from before
_USER_TEMPLATE = "Parse the following resume into the JSON schema. Return ONLY the JSON object.\n\n---RESUME START---\n{raw_text}\n---RESUME END---"

# ── JSON extraction helpers ───────────────────────────────────────────────────
def _try_parse(text: str) -> dict | None:
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        return None

def _extract_json(raw: str) -> dict:
    result = _try_parse(raw)
    if result is not None: return result
    stripped = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped.strip())
    result = _try_parse(stripped)
    if result is not None: return result
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        result = _try_parse(m.group(0))
        if result is not None: return result
    raise ValueError(f"The model did not return valid JSON.\n\nRaw response:\n{raw[:600]}")

def _empty_resume() -> dict:
    return {
        "contact": {"name": "", "email": "", "phone": "", "location": "", "linkedin": "", "github": ""},
        "summary": "",
        "experience": [],
        "education": [],
        "skills": {"technical": [], "soft": []},
    }

def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result

# ── Public API ────────────────────────────────────────────────────────────────
def structure_resume(raw_text: str, model: str = "llama-3.1-8b-instant") -> dict:
    """Send text to Groq API instead of local Ollama."""
    
    # Securely grab the API key from Streamlit Secrets
    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Groq API key not found. Please add it to Streamlit Secrets.")

    client = Groq(api_key=api_key)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_TEMPLATE.format(raw_text=raw_text)},
        ],
        temperature=0.05,
        response_format={"type": "json_object"} # Groq natively supports JSON mode!
    )

    raw_content: str = response.choices[0].message.content
    parsed = _extract_json(raw_content)
    return _deep_merge(_empty_resume(), parsed)
