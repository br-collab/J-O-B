"""
resume_rewriter.py

Takes the analyzer result and the original resume text.
Sends both to OpenAI with strict grounding rules.
Returns a section-by-section rewrite with no hallucinations.
"""

import json
import os
from typing import Any, Dict


def get_openai_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st
        return str(st.secrets.get("OPENAI_API_KEY", "")).strip()
    except Exception:
        return ""


def get_openai_model() -> str:
    model = os.getenv("OPENAI_MODEL", "").strip()
    if model:
        return model
    try:
        import streamlit as st
        return str(st.secrets.get("OPENAI_MODEL", "")).strip() or "gpt-4o-mini"
    except Exception:
        return "gpt-4o-mini"


SYSTEM_PROMPT = """You are a senior executive resume writer with deep expertise in investment management,
asset management, and institutional finance. Your job is to rewrite resume sections to better match
a specific job description using ONLY facts already present in the original resume text.

STRICT RULES:
1. NEVER invent, fabricate, or imply experience, tools, firms, titles, metrics, or outcomes
   not explicitly stated in the original resume text.
2. NEVER change dates, titles, firm names, or dollar amounts.
3. NEVER add certifications, degrees, or qualifications not already listed.
4. You MAY reframe existing experience using the job description vocabulary where the
   underlying meaning is equivalent and factually supported.
5. Every rewritten bullet must be traceable to a specific fact in the original resume.
6. Bullets must be 1-2 lines maximum. Executive register. Lead with business outcome or impact.
7. Active voice. Past tense for prior roles, present tense for current role.
8. No filler phrases: leveraged, utilized, spearheaded, dynamic, passionate, results-driven.
9. Summary must be 3-4 sentences maximum. No buzzword stacking.
10. Return ONLY valid JSON. No markdown fences. No preamble.

OUTPUT FORMAT:
{
  "summary": "rewritten professional summary",
  "experience": [
    {
      "role": "exact role title from original",
      "firm": "exact firm name from original",
      "dates": "exact dates from original",
      "bullets": ["bullet 1", "bullet 2"]
    }
  ],
  "skills": "rewritten skills section as a single string preserving all original skills",
  "grounding_notes": ["note explaining each major reframe and which original fact supports it"]
}"""


def build_rewrite_prompt(
    resume_text: str,
    analysis_result: Dict[str, Any],
    user_feedback: str = "",
) -> str:
    jd_title = analysis_result.get("job_sections", {}).get("title", "Target Role")
    missing = analysis_result.get("missing_keywords", [])
    under_labeled = analysis_result.get("missing_signal_analysis", {}).get("under_labeled", [])
    key_terms = analysis_result.get("key_terms_from_job_description", [])
    top_skills = analysis_result.get("top_skills", [])

    feedback_block = ""
    if user_feedback.strip():
        feedback_block = f"""
HUMAN FEEDBACK ON PREVIOUS DRAFT:
{user_feedback.strip()}
Incorporate this feedback while maintaining all grounding rules.
"""

    return f"""ORIGINAL RESUME TEXT (ground truth - do not contradict or embellish):
{resume_text}

TARGET ROLE: {jd_title}

ANALYZER FINDINGS:
- Already strong (keep prominent): {json.dumps(top_skills)}
- Under-labeled signals (present but not clearly surfaced): {json.dumps(under_labeled)}
- Missing keywords to add IF factually supported: {json.dumps(missing)}
- Key JD terms to mirror where truthful: {json.dumps(key_terms)}
{feedback_block}
TASK:
Rewrite the resume to maximize alignment with the target role.
Use only facts from the original resume text above.
Flag every significant reframe in grounding_notes.
Return valid JSON only."""


def rewrite_resume(
    resume_text: str,
    analysis_result: Dict[str, Any],
    user_feedback: str = "",
) -> Dict[str, Any]:
    from openai import OpenAI

    api_key = get_openai_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    model = get_openai_model()

    user_prompt = build_rewrite_prompt(resume_text, analysis_result, user_feedback)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").replace("json", "", 1).strip()

    parsed = json.loads(raw)

    for key in ("summary", "experience", "skills", "grounding_notes"):
        if key not in parsed:
            parsed[key] = [] if key in ("experience", "grounding_notes") else ""

    return parsed
