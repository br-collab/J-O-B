import json
import os
from typing import Any, Dict

from openai import OpenAI


def get_streamlit_secret(key: str) -> str:
    try:
        import streamlit as st
    except Exception:
        return ""

    try:
        value = st.secrets.get(key, "")
    except Exception:
        return ""
    return str(value).strip()


def get_openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip() or get_streamlit_secret("OPENAI_API_KEY")


def get_openai_model() -> str:
    return (
        os.getenv("OPENAI_MODEL", "").strip()
        or get_streamlit_secret("OPENAI_MODEL")
        or "gpt-5-mini"
    )


DEFAULT_MODEL = get_openai_model()
MAX_ALIGNMENT_ITEMS = 5
MAX_MISSING_ITEMS = 5
MAX_EDIT_ITEMS = 5
MAX_BULLET_ITEMS = 4


def has_openai_api_key() -> bool:
    return bool(get_openai_api_key())


def build_enhancement_payload(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "baseline_score": analysis_result["resume_strength_score"],
        "fit_band": analysis_result["fit_band"],
        "score_disclaimer": analysis_result["score_disclaimer"],
        "raid_breakdown": analysis_result["raid_breakdown"],
        "score_breakdown": analysis_result["score_breakdown"],
        "section_scores": analysis_result["section_scores"],
        "job_sections": analysis_result["job_sections"],
        "resume_sections": analysis_result["resume_sections"],
        "top_skills": analysis_result["top_skills"],
        "missing_keywords": analysis_result["missing_keywords"],
        "missing_signal_analysis": analysis_result["missing_signal_analysis"],
        "key_terms_from_job_description": analysis_result["key_terms_from_job_description"],
        "role_family_buckets": analysis_result["role_family_buckets"],
        "evidence_clusters": analysis_result["evidence_clusters"],
        "resume_cleaned_text": analysis_result["resume_cleaned_text"][:12000],
        "job_focus_text": analysis_result.get("job_focus_text", analysis_result["job_text"])[:12000],
    }


def build_messages(analysis_result: Dict[str, Any]) -> tuple[str, str]:
    payload = build_enhancement_payload(analysis_result)

    system_prompt = (
        "You are a senior resume strategist. "
        "Assess candidate-role fit realistically and conservatively. "
        "Use the baseline local analyzer as the primary evidence source, and do not replace its score. "
        "Treat the score as a resume-strength estimate for this role, not a literal ATS score. "
        "Give special attention to under-labeled executive, governance, and business-manager evidence. "
        "Differentiate explicit evidence from inferred translated fit. "
        "Write like an experienced recruiter or executive career coach: concise, direct, and commercially credible. "
        "Avoid consultant fluff, generic filler, and repetitive restatements of the same concept. "
        "Do not use parentheses unless essential. "
        "Return valid JSON only with this shape: "
        '{"fit_summary": string, "strongest_alignments": [string], '
        '"missing_signals": [string], "recommended_edits": [string], '
        '"rewritten_summary": string, "suggested_bullets": [string], '
        '"confidence_note": string}. '
        "Do not include markdown fences."
    )

    user_prompt = (
        "Analyze this resume against this job description.\n\n"
        "Use these inputs:\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Instructions:\n"
        "- Explain professional fit in plain business language.\n"
        "- Keep fit_summary to 120 words or fewer.\n"
        "- Prefer phrase-level and concept-level reasoning over isolated words.\n"
        "- Treat responsibilities and required qualifications as more important than preferred qualifications.\n"
        "- Distinguish explicit evidence, under-labeled evidence, and true missing signals.\n"
        "- Do not repeat the same idea across multiple sections unless it materially changes the recommendation.\n"
        "- Missing signals must be realistic, not generic noise.\n"
        "- strongest_alignments: 3 to 5 concise bullets.\n"
        "- missing_signals: 3 to 5 concise bullets.\n"
        "- recommended_edits: 3 to 5 concise bullets ordered by highest impact.\n"
        "- Suggested bullets should sound professional and measurable where possible.\n"
        "- suggested_bullets: 2 to 4 bullets only.\n"
        "- The rewritten summary should be concise and credible, with no more than 90 words.\n"
        "- Only suggest edits that can be plausibly supported by the existing resume evidence.\n"
        "- The confidence note must state that the output is interpretive and not authoritative ATS truth.\n"
    )

    return system_prompt, user_prompt


def parse_json_response(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    return json.loads(cleaned)


def clean_text_item(value: Any) -> str:
    text = str(value or "").strip()
    text = " ".join(text.split())
    return text


def normalize_list(values: Any, limit: int) -> list[str]:
    results = []
    seen = set()
    for value in values or []:
        text = clean_text_item(value)
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        results.append(text)
        if len(results) >= limit:
            break
    return results


def enhance_analysis_with_openai(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    if not has_openai_api_key():
        raise ValueError("OPENAI_API_KEY is not set.")

    system_prompt, user_prompt = build_messages(analysis_result)
    client = OpenAI(api_key=get_openai_api_key())

    response = client.responses.create(
        model=DEFAULT_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    parsed = parse_json_response(response.output_text)
    return {
        "model": DEFAULT_MODEL,
        "fit_summary": clean_text_item(parsed.get("fit_summary", "")),
        "strongest_alignments": normalize_list(
            parsed.get("strongest_alignments", []),
            MAX_ALIGNMENT_ITEMS,
        ),
        "missing_signals": normalize_list(
            parsed.get("missing_signals", []),
            MAX_MISSING_ITEMS,
        ),
        "recommended_edits": normalize_list(
            parsed.get("recommended_edits", []),
            MAX_EDIT_ITEMS,
        ),
        "rewritten_summary": clean_text_item(parsed.get("rewritten_summary", "")),
        "suggested_bullets": normalize_list(
            parsed.get("suggested_bullets", []),
            MAX_BULLET_ITEMS,
        ),
        "confidence_note": clean_text_item(parsed.get("confidence_note", "")),
    }
