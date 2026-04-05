"""
job_scout.py

Polls public job board APIs (Greenhouse, Lever) for target firms.
Filters by target titles and returns roles ranked by analyzer fit score.
No authentication required — these endpoints are publicly accessible.
"""

import re
import urllib.request
import urllib.error
import json
from typing import Any

# ---------------------------------------------------------------------------
# Target firm configuration
# Each entry maps a display name to its job board handle and API type.
# Greenhouse board token: visible in the careers page URL at
#   https://boards.greenhouse.io/<token>
# Lever posting URL: https://api.lever.co/v0/postings/<handle>
# ---------------------------------------------------------------------------

TARGET_FIRMS: list[dict[str, str]] = [
    {"name": "BlackRock",     "handle": "blackrock",       "api": "greenhouse"},
    {"name": "American Express", "handle": "americanexpress", "api": "greenhouse"},
    {"name": "AT&T",          "handle": "att",             "api": "greenhouse"},
    {"name": "JPMorgan Chase","handle": "jpmorgan",        "api": "greenhouse"},
    {"name": "Goldman Sachs", "handle": "goldmansachs",    "api": "greenhouse"},
    {"name": "Morgan Stanley","handle": "morganstanley",   "api": "greenhouse"},
    {"name": "Citigroup",     "handle": "citi",            "api": "greenhouse"},
    {"name": "McKinsey",      "handle": "mckinsey",        "api": "lever"},
    {"name": "BCG",           "handle": "bcg",             "api": "lever"},
]

# ---------------------------------------------------------------------------
# Title keywords — roles that match any of these terms are surfaced.
# Lowercased for comparison.
# ---------------------------------------------------------------------------

TARGET_TITLE_KEYWORDS: list[str] = [
    "chief of staff",
    "business manager",
    "operating lead",
    "strategic advisor",
    "chief data",
    "executive director",
    "head of",
    "transformation",
    "governance",
    "program manager",
    "portfolio manager",
    "treasury",
    "institutional",
]

FETCH_TIMEOUT_SECONDS = 8


def _fetch_json(url: str) -> Any:
    """Fetch a URL and return parsed JSON, or None on error."""
    try:
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, Exception):
        return None


def _title_matches(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in TARGET_TITLE_KEYWORDS)


def _fetch_greenhouse_roles(firm: dict[str, str]) -> list[dict[str, str]]:
    handle = firm["handle"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{handle}/jobs?content=true"
    data = _fetch_json(url)
    if not data or "jobs" not in data:
        return []

    roles = []
    for job in data["jobs"]:
        title = job.get("title", "")
        if not _title_matches(title):
            continue
        roles.append({
            "firm": firm["name"],
            "title": title,
            "location": job.get("location", {}).get("name", "Not listed"),
            "url": job.get("absolute_url", ""),
            "description": _strip_html(job.get("content", "")),
            "source": "Greenhouse",
        })
    return roles


def _fetch_lever_roles(firm: dict[str, str]) -> list[dict[str, str]]:
    handle = firm["handle"]
    url = f"https://api.lever.co/v0/postings/{handle}?mode=json"
    data = _fetch_json(url)
    if not isinstance(data, list):
        return []

    roles = []
    for posting in data:
        title = posting.get("text", "")
        if not _title_matches(title):
            continue
        location_obj = posting.get("categories", {})
        location = location_obj.get("location", "Not listed")
        description_parts = posting.get("descriptionPlain", "") or ""
        roles.append({
            "firm": firm["name"],
            "title": title,
            "location": location,
            "url": posting.get("hostedUrl", ""),
            "description": description_parts[:3000],
            "source": "Lever",
        })
    return roles


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:3000]


def fetch_target_roles() -> list[dict[str, str]]:
    """
    Poll all target firms and return matching roles.
    Returns a flat list of role dicts, unsorted.
    """
    all_roles: list[dict[str, str]] = []
    for firm in TARGET_FIRMS:
        if firm["api"] == "greenhouse":
            all_roles.extend(_fetch_greenhouse_roles(firm))
        elif firm["api"] == "lever":
            all_roles.extend(_fetch_lever_roles(firm))
    return all_roles


def score_roles_against_resume(
    roles: list[dict[str, Any]],
    resume_file: Any,
) -> list[dict[str, Any]]:
    """
    Run the existing analyzer against each fetched role.
    resume_file: a Streamlit UploadedFile (or any file-like with .name, .read(), .seek()).
    Returns roles sorted by fit score descending.
    """
    from analyzer import analyze_resume_text_against_job_text

    scored = []
    for role in roles:
        description = role.get("description", "")
        if not description or len(description.strip()) < 100:
            role["score"] = None
            role["fit_band"] = "Insufficient description"
            role["top_skills"] = []
            role["missing_keywords"] = []
            scored.append(role)
            continue

        try:
            resume_file.seek(0)
            result = analyze_resume_text_against_job_text(
                resume_file,
                description,
                job_filename=f"{role['firm']}_{role['title'][:40]}.txt",
            )
            role["score"] = result["resume_strength_score"]
            role["fit_band"] = result["fit_band"]
            role["top_skills"] = result["top_skills"][:5]
            role["missing_keywords"] = result["missing_keywords"][:5]
        except Exception:
            role["score"] = None
            role["fit_band"] = "Error during scoring"
            role["top_skills"] = []
            role["missing_keywords"] = []

        scored.append(role)

    scored.sort(key=lambda r: r["score"] or 0, reverse=True)
    return scored
