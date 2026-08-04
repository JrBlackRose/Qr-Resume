"""
Resume structuring via the Groq API (Cloud).
Runs Llama 3.3 instantly and for free, with no local GPU required.
"""
from __future__ import annotations
import json
import re
import os
import streamlit as st
from groq import Groq

# ── Prompt ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert ATS (Applicant Tracking System) resume parser. Your ONLY job is to read the raw resume text and extract the data into a single, valid JSON object.

STRICT INSTRUCTIONS:
1. Respond ONLY with raw, valid JSON. No markdown fences (```), no explanations.
2. Name: The candidate's full name is usually the very first line of the text.
3. Summary: Extract the ENTIRE professional summary paragraph. Do NOT truncate it.
4. Experience: Include ALL work experience, freelance roles, AND academic/personal projects in the "experience" array.
5. Skills: Categorize all extracted skills into "technical" or "soft" arrays. Certifications can be added to technical skills.
6. Missing data: Use "" for missing strings and [] for missing arrays. Do NOT invent data.

Required JSON schema:
{
  "contact": {
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1 234 567 8900",
    "location": "City, State / Country",
    "linkedin": "[linkedin.com/in/username](https://linkedin.com/in/username)",
    "github": "[github.com/username](https://github.com/username)"
  },
  "summary": "Full professional summary paragraph here...",
  "experience": [
    {
      "title": "Job or Project Title",
      "company": "Company Name or University",
      "location": "City, State or Remote",
      "start_date": "Month Year",
      "end_date": "Month Year or Present",
      "bullets": [
        "Extracted bullet point 1.",
        "Extracted bullet point 2."
      ]
    }
  ],
  "education": [
    {
      "degree": "Degree Name",
      "institution": "University Name",
      "location": "City, State",
      "graduation_date": "Month Year",
      "gpa": "GPA if listed"
    }
  ],
  "skills": {
    "technical": ["Skill 1", "Skill 2"],
    "soft": ["Skill 3"]
  }
}
"""

_USER_TEMPLATE = (
    "Parse the following resume into the JSON schema. Return ONLY the JSON object.\n\n"
    "---RESUME START---\n{raw_text}\n---RESUME END---"
)


# ── JSON extraction helpers ───────────────────────────────────────────────────

def _try_parse(text: str) -> dict | None:
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        return None

def _extract_json(raw: str) -> dict:
    result = _try_parse(raw)
    if result is not None:
        return result
    stripped = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped.strip())
    result = _try_parse(stripped)
    if result is not None:
        return result
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        result = _try_parse(m.group(0))
        if result is not None:
            return result
    raise ValueError(
        "The model did not return valid JSON.\n\n"
        f"Raw response:\n{raw[:600]}"
    )

def _empty_resume() -> dict:
    return {
        "contact": {
            "name": "", "email": "", "phone": "",
            "location": "", "linkedin": "", "github": "",
        },
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

def structure_resume(raw_text: str, model: str = "llama-3.3-70b-versatile") -> dict:
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
        response_format={"type": "json_object"}
    )

    raw_content: str = response.choices[0].message.content
    parsed = _extract_json(raw_content)
    return _deep_merge(_empty_resume(), parsed)
