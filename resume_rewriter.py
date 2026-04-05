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


SYSTEM_PROMPT = """You are a senior executive resume strategist specializing in MD-level financial services placements.
Your job is NOT to rewrite resumes from scratch. Your job is surgical vocabulary reframing —
preserve the candidate's original bullets, metrics, and structure almost entirely,
and make the minimum changes needed to mirror the target role's language.

CORE PHILOSOPHY — LIGHT TOUCH ONLY:
The original resume bullets are already strong. A $500 resume writer does not replace
strong bullets with weaker prose. They make precise swaps: one phrase for another,
where the swap is truthful and makes the candidate sound like they already speak the employer's language.

STRICT RULES:
1. NEVER invent, fabricate, or imply experience, tools, firms, titles, metrics, or outcomes
   not in the original resume. Not even plausibly. Not even as implication.
2. NEVER change dates, firm names, dollar amounts, percentages, or headcounts.
3. NEVER soften strong verbs. "Restored $420M" stays "Restored $420M" — not "Resolved" or "Addressed."
4. NEVER replace a specific metric with a vague description.
5. NEVER add bullets — only reframe existing ones.
6. Preserve the original bullet count per role exactly.
7. Vocabulary swaps ONLY where the JD uses materially better language for the same concept:
   e.g. "forward-deployed" for "embedded consultant", "systematic change" for "transformation",
   "target operating model" for "operating model redesign". These are direct equivalents — swap them.
8. If a bullet already uses strong language that matches the JD intent, leave it unchanged.
9. Summary: reframe the opening 1-2 sentences to echo the JD's framing. Keep sentences 3-4 unchanged.
   Maximum 4 sentences. No buzzword stacking. No filler.
10. Banned words: utilized, leveraged, spearheaded, dynamic, passionate, results-driven, ensured, facilitated.
11. Return ONLY valid JSON. No markdown fences. No preamble.

OUTPUT FORMAT:
{
  "summary": "lightly reframed professional summary — max 4 sentences",
  "experience": [
    {
      "role": "exact role title from original",
      "firm": "exact firm name from original",
      "dates": "exact dates from original",
      "bullets": ["original bullet with minimal targeted vocabulary swap if needed"]
    }
  ],
  "skills": "original skills string — only add missing JD terms if they are truthfully present in resume",
  "grounding_notes": ["one note per change made — what changed, why, which original fact supports it"]
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
Apply this feedback precisely. Do not over-correct. Maintain all grounding rules.
"""

    return f"""ORIGINAL RESUME TEXT — this is the ground truth. Preserve it. Reframe minimally.
{resume_text}

TARGET ROLE: {jd_title}

ANALYZER FINDINGS — use these to guide vocabulary swaps only:
- Already strong, keep exactly as written: {json.dumps(top_skills)}
- Under-labeled signals (present but not surfaced — reframe these bullets to name the concept): {json.dumps(under_labeled)}
- Missing keywords — add ONLY if the underlying experience is already in the resume: {json.dumps(missing)}
- Key JD terms to mirror where the swap is a true equivalent: {json.dumps(key_terms)}
{feedback_block}
TASK:
Make the minimum vocabulary changes needed to align this resume with the target role.
Every original bullet should be recognizable in the output — same metric, same outcome, same structure.
Only change words where the JD language is a genuine improvement over the original.
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
        temperature=0.15,
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
