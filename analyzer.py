from collections import Counter
import json
from pathlib import Path

from utils import (
    extract_text_with_metadata,
    infer_resume_sections,
    preprocess_text,
    split_job_description_sections,
    split_resume_sections,
)


DOMAIN_TERMS = {
    "analytics",
    "banking",
    "capital",
    "control",
    "custody",
    "data",
    "equity",
    "financial",
    "governance",
    "implementation",
    "institutional",
    "investment",
    "liquidity",
    "markets",
    "model",
    "operating",
    "portfolio",
    "regulatory",
    "reporting",
    "risk",
    "strategy",
    "treasury",
}

PLATFORM_TERMS = {
    "aladdin",
    "analytics",
    "crm",
    "dashboard",
    "data",
    "governance",
    "modeling",
    "oms",
    "platform",
    "portfolio",
    "reporting",
    "sap",
    "salesforce",
    "sql",
    "tableau",
}

SENIORITY_TERMS = {
    "advisor",
    "associate",
    "chief",
    "director",
    "executive",
    "head",
    "lead",
    "manager",
    "principal",
    "senior",
    "vice",
}

SECTION_WEIGHTS = {
    "summary": 0.30,
    "skills": 0.20,
    "experience": 0.35,
    "education": 0.15,
}

SCORE_WEIGHTS = {
    "phrase_overlap": 0.12,
    "keyword_overlap": 0.05,
    "skills_domain_match": 0.17,
    "seniority_alignment": 0.12,
    "section_alignment": 0.10,
    "translation_fit": 0.22,
    "evidence_alignment": 0.22,
}

PHRASE_LIBRARY = {
    "ai enabled solutions",
    "ai governance",
    "analytics office",
    "analytics overviews",
    "business manager",
    "capital markets",
    "chief data",
    "chief data office",
    "chief data analytics office",
    "chief of staff",
    "client transformation",
    "client transformations",
    "control framework",
    "cross functional",
    "data analytics",
    "data integration",
    "data validation",
    "data visualization",
    "decision briefings",
    "decision ready",
    "delivery lead",
    "enterprise transformation",
    "enterprise wide transformation",
    "executive director",
    "executive materials",
    "executive reporting",
    "executive updates",
    "financial oversight",
    "forward deployed",
    "governance rhythm",
    "headcount management",
    "implementation governance",
    "institutional clients",
    "institutional custody",
    "internal governance",
    "investment management",
    "investment banking",
    "investment workflow",
    "kpi reporting",
    "leadership routines",
    "liquidity management",
    "machine learning",
    "matrixed organizations",
    "operating cadence",
    "operating governance",
    "operating lead",
    "operating model",
    "platform implementation",
    "platform integration",
    "portfolio analytics",
    "portfolio management",
    "prioritization framework",
    "qbrs",
    "regulatory reporting",
    "resource planning",
    "roi modeling",
    "stakeholder alignment",
    "stakeholder coordination",
    "stakeholder management",
    "status reporting",
    "strategic advisor",
    "strategic change",
    "systematic change",
    "target operating model",
    "treasury operations",
    "trusted advisor",
    "workflow automation",
    "workflow transformation",
    "value creation",
}

NGRAM_CONTEXT_TERMS = {
    "alignment",
    "analytics",
    "business",
    "cadence",
    "coordination",
    "data",
    "director",
    "executive",
    "financial",
    "governance",
    "leadership",
    "management",
    "materials",
    "model",
    "office",
    "operating",
    "operations",
    "oversight",
    "reporting",
    "review",
    "routine",
    "routines",
    "stakeholder",
    "status",
}

TRANSLATION_MAP = {
    "chief of staff": {"business manager", "operating lead", "strategic advisor"},
    "business manager": {"chief of staff", "operating lead", "trusted advisor"},
    "executive materials": {"decision briefings", "qbrs", "executive reporting"},
    "leadership routines": {"operating cadence", "governance rhythm", "operating reviews"},
    "status reporting": {"command reporting", "kpi reporting", "executive updates"},
    "governance": {"control framework", "operating governance", "decision governance"},
    "stakeholder coordination": {"stakeholder management", "stakeholder alignment", "cross functional"},
    "ai enabled solutions": {"ai governance", "workflow transformation", "data analytics"},
    "forward deployed": {"principal consultant", "implementation governance", "strategic advisor"},
    "enterprise transformation": {"platform transformation", "workflow transformation", "operating model"},
    "systematic change": {"enterprise transformation", "operating model", "workflow transformation"},
    "strategic change": {"transformation", "operating model", "strategic advisor"},
    "target operating model": {"operating model", "implementation governance", "workflow transformation"},
    "workflow automation": {"ai enabled solutions", "intelligent document processing", "workflow transformation"},
    "principal consultant": {"forward deployed", "strategic advisor", "trusted advisor"},
    "implementation governance": {"control framework", "operating governance", "enterprise transformation"},
    "decision ready": {"executive materials", "decision briefings", "executive reporting"},
    "roi modeling": {"financial oversight", "kpi reporting", "value creation"},
    # Aladdin / investment platform delivery vocabulary
    "client transformation": {"implementation governance", "platform implementation", "enterprise transformation"},
    "client transformations": {"implementation governance", "platform implementation", "enterprise transformation"},
    "delivery lead": {"implementation governance", "operating lead", "principal consultant"},
    "investment workflow": {"operating model", "workflow transformation", "platform implementation"},
    "platform implementation": {"implementation governance", "client transformation", "enterprise transformation"},
    "platform integration": {"api driven platform integration", "implementation governance", "workflow transformation"},
    "analytics overviews": {"data analytics", "portfolio analytics", "data visualization"},
    "data visualization": {"data analytics", "predictive analytics", "portfolio analytics"},
    "data integration": {"api driven platform integration", "intelligent document processing", "workflow automation"},
    "portfolio management": {"portfolio analytics", "investment management", "institutional clients"},
}

ROLE_BUCKETS = {
    "Leadership / Business Management": {
        "business manager",
        "chief of staff",
        "executive director",
        "operating lead",
        "resource planning",
        "stakeholder coordination",
        "stakeholder management",
        "strategic advisor",
        "trusted advisor",
    },
    "Governance / Cadence": {
        "control framework",
        "executive materials",
        "governance",
        "governance rhythm",
        "internal governance",
        "kpi reporting",
        "leadership routines",
        "operating cadence",
        "operating governance",
        "status reporting",
    },
    "Data / Analytics / AI": {
        "ai enabled solutions",
        "ai governance",
        "analytics office",
        "chief data",
        "chief data office",
        "data analytics",
    },
    "Financial Services Domain": {
        "capital markets",
        "financial oversight",
        "institutional custody",
        "investment banking",
        "liquidity management",
        "portfolio analytics",
        "regulatory reporting",
        "treasury operations",
    },
    "Tools / Platforms": {
        "aladdin",
        "crm",
        "oms",
        "salesforce",
        "sap",
        "sql",
        "tableau",
    },
}

TAXONOMY_PATH = Path(__file__).resolve().parent / "taxonomy" / "taxonomy_library.json"


def load_taxonomy_library():
    if not TAXONOMY_PATH.exists():
        return {}
    try:
        return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


TAXONOMY_LIBRARY = load_taxonomy_library()
TAXONOMY_PHRASES = set(TAXONOMY_LIBRARY.get("mined_phrase_library", []))
TAXONOMY_BUCKET_TERMS = {
    name: set(values)
    for name, values in TAXONOMY_LIBRARY.get("bucket_terms", {}).items()
}
MERGED_PHRASE_LIBRARY = set(PHRASE_LIBRARY) | TAXONOMY_PHRASES
MERGED_ROLE_BUCKETS = {
    bucket_name: set(ROLE_BUCKETS.get(bucket_name, set())) | TAXONOMY_BUCKET_TERMS.get(bucket_name, set())
    for bucket_name in set(ROLE_BUCKETS) | set(TAXONOMY_BUCKET_TERMS)
}
TAXONOMY_PRIORITY_TOKENS = {
    "analytics",
    "business",
    "capital",
    "chief",
    "custody",
    "data",
    "director",
    "executive",
    "financial",
    "governance",
    "headcount",
    "kpi",
    "leadership",
    "liquidity",
    "manager",
    "office",
    "operating",
    "platform",
    "portfolio",
    "reporting",
    "resource",
    "risk",
    "stakeholder",
    "strategy",
    "treasury",
}

EVIDENCE_CLUSTERS = {
    "business_manager_leadership": {
        "label": "Business manager / chief of staff leadership",
        "terms": {
            "business manager",
            "chief of staff",
            "trusted advisor",
            "operating lead",
            "strategic advisor",
            "office of the ceo",
            "office of the coo",
        },
        "weight": 1.2,
    },
    "executive_communications": {
        "label": "Executive communications",
        "terms": {
            "executive materials",
            "executive reporting",
            "executive updates",
            "decision briefings",
            "briefing documents",
            "talking points",
            "qbrs",
            "presentations",
        },
        "weight": 1.1,
    },
    "governance_cadence": {
        "label": "Governance and operating cadence",
        "terms": {
            "leadership routines",
            "operating cadence",
            "governance rhythm",
            "executive governance",
            "cross functional governance",
            "internal governance",
            "operating governance",
            "operational reviews",
        },
        "weight": 1.15,
    },
    "stakeholder_management": {
        "label": "Stakeholder coordination",
        "terms": {
            "stakeholder management",
            "stakeholder alignment",
            "stakeholder coordination",
            "internal stakeholders",
            "senior stakeholders",
            "cross functional",
            "client engagement",
        },
        "weight": 1.05,
    },
    "kpi_status_reporting": {
        "label": "KPI and status reporting",
        "terms": {
            "status reporting",
            "kpi reporting",
            "performance metrics",
            "okr tracking",
            "command reporting",
            "operational risk metrics",
        },
        "weight": 1.0,
    },
    "resource_financial_planning": {
        "label": "Resource and financial planning",
        "terms": {
            "resource planning",
            "headcount management",
            "financial oversight",
            "budget",
            "allocation",
            "revenue performance",
        },
        "weight": 0.95,
    },
    "data_analytics_ai": {
        "label": "Data / analytics / AI",
        "terms": {
            "chief data office",
            "chief analytics office",
            "analytics office",
            "data analytics",
            "data governance",
            "sql tableau analytics",
            "ai governance",
            "ai enabled solutions",
            "data driven",
        },
        "weight": 1.1,
    },
    "financial_services_domain": {
        "label": "Financial-services domain",
        "terms": {
            "capital markets",
            "custody",
            "post trade operations",
            "settlement",
            "liquidity",
            "structured credit",
            "institutional platforms",
            "treasury infrastructure",
        },
        "weight": 1.0,
    },
    "transformation_execution": {
        "label": "Transformation and execution",
        "terms": {
            "operating model transformation",
            "workflow transformation",
            "process optimization",
            "platform implementation",
            "platform integration",
            "client transformation",
            "client transformations",
            "investment workflow",
            "cross functional initiatives",
            "strategic initiatives",
            "implementation governance",
            "delivery lead",
        },
        "weight": 0.95,
    },
    "investment_platform_delivery": {
        "label": "Investment platform delivery",
        "terms": {
            "analytics overviews",
            "data visualization",
            "data integration",
            "data validation",
            "investment workflow",
            "portfolio management",
            "platform implementation",
            "client transformation",
            "go live",
            "production go live",
        },
        "weight": 1.0,
    },
}


def compute_cosine_similarity(a, b):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    if not a.strip() or not b.strip():
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 3))
    vectors = vectorizer.fit_transform([a, b])
    return float(cosine_similarity(vectors[0], vectors[1])[0][0] * 100)


def extract_ngrams(tokens, min_n=2, max_n=3):
    ngrams = []
    for size in range(min_n, max_n + 1):
        for index in range(len(tokens) - size + 1):
            ngrams.append(" ".join(tokens[index : index + size]))
    return ngrams


def extract_known_phrases(normalized_text):
    found = []
    for phrase in MERGED_PHRASE_LIBRARY:
        if phrase not in normalized_text:
            continue
        tokens = set(phrase.split())
        if phrase not in PHRASE_LIBRARY and not (tokens & TAXONOMY_PRIORITY_TOKENS):
            continue
        found.append(phrase)
    return sorted(found, key=lambda phrase: (-len(phrase.split()), phrase))


def dedupe_keep_order(items):
    results = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        results.append(item)
    return results


NOISE_BIGRAM_PATTERNS = {
    "clientfacing", "executivelatam", "skillfull", "governanceoperational",
    "managementmarkets", "generativegovernance", "financialservices",
    "largefinancial", "marketfinancial", "mandatoryreporting",
}

NOISE_BIGRAM_PAIRS = {
    ("client", "facing"), ("executive", "latam"), ("skills", "financial"),
    ("governance", "operational"), ("management", "markets"),
    ("generative", "governance"), ("large", "financial"),
    ("market", "financial"), ("mandatory", "reporting"),
    ("financial", "institution"), ("financial", "services"),
    ("frameworks", "financial"),
}

def _is_noise_phrase(phrase: str) -> bool:
    """Reject bigrams that are PDF extraction artifacts, not real role phrases."""
    tokens = phrase.split()
    if len(tokens) == 2:
        pair = (tokens[0], tokens[1])
        if pair in NOISE_BIGRAM_PAIRS:
            return True
    if len(tokens) >= 2:
        joined = "".join(tokens)
        if joined in NOISE_BIGRAM_PATTERNS:
            return True
    return False


def extract_priority_phrases(preprocessed):
    known = sorted(
        extract_known_phrases(preprocessed["normalized_text"]),
        key=lambda phrase: (phrase not in PHRASE_LIBRARY, -len(phrase.split()), phrase),
    )
    if len(known) >= 4:
        return known[:12]

    candidate_ngrams = []
    for phrase in extract_ngrams(preprocessed["filtered_tokens"]):
        if _is_noise_phrase(phrase):
            continue
        tokens = phrase.split()
        if not any(token in DOMAIN_TERMS or token in PLATFORM_TERMS or token in SENIORITY_TERMS for token in tokens):
            continue
        if not any(token in NGRAM_CONTEXT_TERMS for token in tokens):
            continue
        candidate_ngrams.append(phrase)

    ranked = dedupe_keep_order(known + candidate_ngrams)
    return ranked[:12]


def build_job_focus_text(job_sections, fallback_text):
    priority_chunks = []
    title = job_sections.get("title", "").strip()
    responsibilities = job_sections.get("responsibilities", "").strip()
    required = job_sections.get("required_qualifications", "").strip()
    preferred = job_sections.get("preferred_qualifications", "").strip()

    if title:
        priority_chunks.extend([title] * 3)
    if responsibilities:
        priority_chunks.extend([responsibilities] * 3)
    if required:
        priority_chunks.extend([required] * 3)
    if preferred:
        priority_chunks.append(preferred)

    if not priority_chunks:
        return fallback_text

    priority_chunks.append(fallback_text)
    return "\n".join(chunk for chunk in priority_chunks if chunk).strip()


def compute_overlap_percentage(resume_items, job_items):
    if not job_items:
        return 0.0
    resume_set = set(resume_items)
    job_set = set(job_items)
    return (len(resume_set & job_set) / len(job_set)) * 100


def compute_phrase_overlap_with_translation(resume_phrases, job_phrases, resume_normalized_text):
    """
    Phrase overlap that awards partial credit when a JD phrase is absent
    but its translation equivalent is present in the resume.

    Calibrated from real outcomes:
    - JPMC 66% (Under Consideration): translation_fit 100%, phrase_overlap 8.3%
      — literal overlap understated true fit significantly
    - WF 82% (Interview): translation_fit 100%, phrase_overlap 25%
      — literal overlap was closer to true fit

    Translation credit: 0.6 of a full match (not 0 and not 1).
    This prevents over-rewarding pure translation with no literal evidence.
    """
    if not job_phrases:
        return 0.0

    resume_set = set(resume_phrases)
    score = 0.0

    for jd_phrase in job_phrases:
        if jd_phrase in resume_set:
            score += 1.0
        else:
            equivalents = TRANSLATION_MAP.get(jd_phrase, set())
            reverse_equivalents = {
                eq
                for term, eqs in TRANSLATION_MAP.items()
                for eq in eqs
                if jd_phrase in eqs and term in resume_set
            }
            all_equivalents = equivalents | reverse_equivalents
            if any(eq in resume_normalized_text for eq in all_equivalents):
                score += 0.6

    return (score / len(job_phrases)) * 100


def has_phrase_evidence(text, phrases):
    return [phrase for phrase in phrases if phrase in text]


def build_evidence_clusters(resume_text, job_sections):
    clusters = {}
    required_text = " ".join(
        part for part in [
            job_sections.get("title", ""),
            job_sections.get("responsibilities", ""),
            job_sections.get("required_qualifications", ""),
        ]
        if part
    ).lower()
    preferred_text = job_sections.get("preferred_qualifications", "").lower()

    for cluster_name, config in EVIDENCE_CLUSTERS.items():
        terms = config["terms"]
        resume_hits = has_phrase_evidence(resume_text, terms)
        required_hits = has_phrase_evidence(required_text, terms)
        preferred_hits = has_phrase_evidence(preferred_text, terms)

        if not required_hits and not preferred_hits:
            continue

        translated_hits = []
        for target in required_hits + preferred_hits:
            if target in resume_hits:
                continue
            equivalents = TRANSLATION_MAP.get(target, set())
            matches = [item for item in equivalents if item in resume_text]
            if matches:
                translated_hits.extend(matches)

        clusters[cluster_name] = {
            "label": config["label"],
            "weight": config["weight"],
            "required_terms": dedupe_keep_order(required_hits),
            "preferred_terms": dedupe_keep_order(preferred_hits),
            "resume_hits": dedupe_keep_order(resume_hits),
            "translated_hits": dedupe_keep_order(translated_hits),
        }

    return clusters


def compute_cluster_alignment(evidence_clusters):
    if not evidence_clusters:
        return 0.0

    weighted_total = 0.0
    weight_sum = 0.0
    for cluster in evidence_clusters.values():
        required_count = len(cluster["required_terms"])
        preferred_count = len(cluster["preferred_terms"])
        possible = required_count + (preferred_count * 0.6)
        if possible <= 0:
            continue

        observed = len(cluster["resume_hits"]) + (len(cluster["translated_hits"]) * 0.85)
        cluster_score = min((observed / possible) * 100, 100)
        weight = cluster["weight"]
        weighted_total += cluster_score * weight
        weight_sum += weight

    if weight_sum == 0:
        return 0.0
    return round(weighted_total / weight_sum, 1)


def compute_translation_fit(resume_text, job_phrases):
    matched = 0
    possible = 0

    for jd_phrase, equivalents in TRANSLATION_MAP.items():
        if jd_phrase not in job_phrases:
            continue
        possible += 1
        if jd_phrase in resume_text or any(option in resume_text for option in equivalents):
            matched += 1

    if not possible:
        return 0.0
    return (matched / possible) * 100


def get_section_body(section_text):
    if not section_text:
        return ""
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    if len(lines) > 1:
        return "\n".join(lines[1:]).strip()
    return section_text.strip()


def compute_summary_fallback_score(resume_sections, job_sections):
    summary_text = get_section_body(resume_sections.get("summary", ""))
    if summary_text:
        return None

    fallback_sources = [
        get_section_body(resume_sections.get("skills", "")),
        get_section_body(resume_sections.get("experience", "")),
    ]
    fallback_resume_text = "\n".join(part for part in fallback_sources if part).strip()
    required_job_text = "\n".join(
        part
        for part in [
            job_sections.get("title", ""),
            job_sections.get("responsibilities", ""),
            job_sections.get("required_qualifications", ""),
        ]
        if part
    ).strip()
    if not fallback_resume_text or not required_job_text:
        return None

    fallback_resume = preprocess_text(fallback_resume_text)
    fallback_job = preprocess_text(required_job_text)
    cosine_score = compute_cosine_similarity(fallback_resume["cleaned_text"], fallback_job["cleaned_text"])
    overlap_score = compute_overlap_percentage(
        fallback_resume["filtered_tokens"],
        fallback_job["filtered_tokens"],
    )
    phrase_score = compute_overlap_percentage(
        extract_known_phrases(fallback_resume["normalized_text"]),
        extract_known_phrases(fallback_job["normalized_text"]),
    )
    return round(max(cosine_score * 0.55, overlap_score * 0.60, phrase_score * 0.70), 1)


def build_section_scores(resume_sections, section_detection, job_text, job_sections):
    scores = {}
    weighted_total = 0.0
    required_text = " ".join(
        part for part in [
            job_sections.get("title", ""),
            job_sections.get("responsibilities", ""),
            job_sections.get("required_qualifications", ""),
        ]
        if part
    )

    for section, weight in SECTION_WEIGHTS.items():
        section_text = resume_sections.get(section, "")
        if not section_text:
            scores[section] = None
            continue
        section_body = get_section_body(section_text)

        section_preprocessed = preprocess_text(section_body)
        job_preprocessed = preprocess_text(job_text)
        cosine_score = compute_cosine_similarity(section_preprocessed["cleaned_text"], job_preprocessed["cleaned_text"])
        overlap_score = compute_overlap_percentage(
            section_preprocessed["filtered_tokens"], job_preprocessed["filtered_tokens"]
        )
        required_overlap = compute_overlap_percentage(
            section_preprocessed["filtered_tokens"],
            preprocess_text(required_text)["filtered_tokens"],
        )
        section_phrase_overlap = compute_overlap_percentage(
            extract_known_phrases(section_preprocessed["normalized_text"]),
            extract_known_phrases(job_preprocessed["normalized_text"]),
        )
        cluster_hits = 0
        cluster_possible = 0
        section_text_normalized = section_preprocessed["normalized_text"]
        for cluster in build_evidence_clusters(section_text_normalized, job_sections).values():
            cluster_possible += len(cluster["required_terms"]) + len(cluster["preferred_terms"])
            cluster_hits += len(cluster["resume_hits"]) + len(cluster["translated_hits"])
        cluster_score = (cluster_hits / cluster_possible) * 100 if cluster_possible else 0.0
        section_score = round(
            max(
                cosine_score,
                overlap_score * 0.9,
                required_overlap,
                section_phrase_overlap * 0.95,
                cluster_score,
            ),
            1,
        )
        scores[section] = section_score
        weighted_total += section_score * weight

    summary_fallback_score = compute_summary_fallback_score(resume_sections, job_sections)
    if scores.get("summary") is None and summary_fallback_score is not None:
        scores["summary"] = summary_fallback_score
        weighted_total += summary_fallback_score * SECTION_WEIGHTS["summary"]
        if section_detection == "detected":
            section_detection = "detected_with_summary_fallback"

    scores["overall"] = round(weighted_total, 1)
    scores["detection"] = section_detection
    return scores


def compute_section_alignment(section_scores, resume_cleaned_text, job_cleaned_text):
    detected_scores = [
        value
        for key, value in section_scores.items()
        if key in SECTION_WEIGHTS and value is not None
    ]
    global_score = compute_cosine_similarity(resume_cleaned_text, job_cleaned_text)

    if not detected_scores:
        return round(global_score * 0.9, 1)

    average_section = sum(detected_scores) / len(detected_scores)
    if section_scores["detection"] == "inferred":
        return round(max(average_section, global_score * 0.9), 1)
    return round(max(average_section, global_score * 0.8), 1)


def build_role_bucket_output(resume_text, job_phrases):
    buckets = {}
    for bucket_name, bucket_terms in MERGED_ROLE_BUCKETS.items():
        seed_terms = ROLE_BUCKETS.get(bucket_name, set())
        job_terms = [term for term in bucket_terms if term in job_phrases]
        job_terms = sorted(
            job_terms,
            key=lambda term: (term not in seed_terms, -len(term.split()), term),
        )[:6]
        matched = [term for term in job_terms if term in resume_text]
        translated = []

        for term in job_terms:
            if term in matched:
                continue
            equivalents = TRANSLATION_MAP.get(term, set())
            evidence = [item for item in equivalents if item in resume_text]
            if evidence:
                translated.append({"job_term": term, "resume_evidence": evidence})

        missing = [
            term
            for term in job_terms
            if term not in matched and term not in {item["job_term"] for item in translated}
        ]

        if matched or translated or missing:
            buckets[bucket_name] = {
                "matched": matched,
                "translated": translated,
                "missing": missing,
            }

    return buckets


def compute_evidence_alignment(role_family_buckets, evidence_clusters):
    total_terms = 0
    bucket_score = 0.0

    for bucket in role_family_buckets.values():
        matched = bucket["matched"]
        translated = bucket["translated"]
        missing = bucket["missing"]
        bucket_total = len(matched) + len(translated) + len(missing)
        if not bucket_total:
            continue
        total_terms += bucket_total
        bucket_score += len(matched) + (len(translated) * 0.85)

    bucket_alignment = (bucket_score / total_terms) * 100 if total_terms else 0.0
    cluster_alignment = compute_cluster_alignment(evidence_clusters)

    if bucket_alignment == 0.0:
        return cluster_alignment
    if cluster_alignment == 0.0:
        return round(bucket_alignment, 1)
    return round((bucket_alignment * 0.4) + (cluster_alignment * 0.6), 1)


def get_top_skills(job_phrases, resume_phrases, resume_tokens, job_tokens, evidence_clusters, limit=8):
    cluster_labels = [
        cluster["label"]
        for cluster in evidence_clusters.values()
        if cluster["resume_hits"] or cluster["translated_hits"]
    ]
    matched_phrases = [phrase for phrase in job_phrases if phrase in resume_phrases]

    matched_tokens = [
        token
        for token, _ in Counter(job_tokens).most_common()
        if token in set(resume_tokens) and token in DOMAIN_TERMS | PLATFORM_TERMS | SENIORITY_TERMS
    ]

    return dedupe_keep_order(cluster_labels + matched_phrases + matched_tokens)[:limit]


def get_missing_terms(
    job_phrases,
    resume_phrases,
    job_tokens,
    resume_tokens,
    evidence_clusters,
    under_labeled_terms=None,
    limit=8,
):
    under_labeled_terms = set(under_labeled_terms or [])
    missing_phrases = [
        phrase for phrase in job_phrases if phrase not in resume_phrases and phrase not in under_labeled_terms
    ]
    missing_tokens = [
        token
        for token, _ in Counter(job_tokens).most_common()
        if token not in set(resume_tokens)
        and token in DOMAIN_TERMS | PLATFORM_TERMS | SENIORITY_TERMS
        and token not in under_labeled_terms
    ]
    prioritized_phrases = sorted(missing_phrases, key=lambda phrase: (-len(phrase.split()), phrase))
    return dedupe_keep_order(prioritized_phrases + missing_tokens)[:limit]


def classify_missing_signals(evidence_clusters, job_phrases, resume_phrases, resume_text, limit=8):
    under_labeled = []
    missing = []

    for cluster in evidence_clusters.values():
        if cluster["required_terms"] and cluster["translated_hits"] and not cluster["resume_hits"]:
            under_labeled.append(cluster["label"])
        elif cluster["required_terms"] and not (cluster["resume_hits"] or cluster["translated_hits"]):
            missing.append(cluster["label"])

    for phrase in job_phrases:
        if phrase in resume_phrases:
            continue
        equivalents = TRANSLATION_MAP.get(phrase, set())
        if equivalents and any(option in resume_text for option in equivalents):
            under_labeled.append(phrase)
        else:
            missing.append(phrase)

    under_labeled = dedupe_keep_order(under_labeled)
    missing = [item for item in dedupe_keep_order(missing) if item not in set(under_labeled)]
    return {
        "under_labeled": under_labeled[:limit],
        "missing": missing[:limit],
    }


def build_suggestions(missing_terms, missing_signal_analysis, score_breakdown, section_scores, detection):
    suggestions = []

    if score_breakdown["phrase_overlap"] < 50:
        suggestions.append("Increase phrase-level alignment using the role's exact business language and operating concepts.")
    if score_breakdown["translation_fit"] < 50:
        suggestions.append("Translate adjacent experience into the role's language, especially around leadership, governance, and executive support.")
    if missing_signal_analysis.get("under_labeled"):
        suggestions.append("Some core signals are present but under-labeled. Rewrite bullets and summaries using clearer business-manager and executive-office language.")
    if section_scores.get("skills") is None:
        suggestions.append("Skills section not clearly detected. Consider adding a clear skills or core competencies section.")
    if section_scores.get("experience") is not None and section_scores["experience"] < 35:
        suggestions.append("Strengthen the experience section with clearer measurable impact and ownership language.")
    if missing_signal_analysis.get("missing"):
        suggestions.append("Add the highest-priority missing signals only where they truthfully reflect your experience and target responsibilities.")
    if any(term in PLATFORM_TERMS for phrase in missing_terms for term in phrase.split()):
        suggestions.append("Add platform and tooling terms where they truthfully reflect your experience.")
    if detection == "inferred":
        suggestions.append("Resume sections were inferred rather than clearly detected, so section scores should be treated cautiously.")

    if not suggestions:
        suggestions.append("The resume shows meaningful fit; refine the strongest bullets to mirror the job's internal business language.")

    return suggestions[:5]


def compute_support_signal(score_breakdown):
    return round(
        (
            score_breakdown["translation_fit"] * 0.30
            + score_breakdown["seniority_alignment"] * 0.20
            + score_breakdown["skills_domain_match"] * 0.30
            + score_breakdown["evidence_alignment"] * 0.20
        ),
        1,
    )


def compute_relevance_score(score_breakdown):
    return round(
        (
            score_breakdown["phrase_overlap"] * 0.35
            + score_breakdown["keyword_overlap"] * 0.15
            + score_breakdown["skills_domain_match"] * 0.20
            + score_breakdown["section_alignment"] * 0.15
            + score_breakdown["evidence_alignment"] * 0.15
        ),
        1,
    )


def get_curated_job_terms(job_sections, job_phrases, evidence_clusters, limit=8):
    curated_terms = []
    title_text = job_sections.get("title", "").lower()
    if title_text:
        curated_terms.extend(
            sorted(
                [phrase for phrase in job_phrases if phrase in title_text],
                key=lambda phrase: (-len(phrase.split()), phrase),
            )
        )

    curated_terms.extend(
        cluster["label"]
        for cluster in evidence_clusters.values()
        if cluster["required_terms"] or cluster["preferred_terms"]
    )
    curated_terms.extend(job_phrases)
    return dedupe_keep_order(curated_terms)[:limit]


def compute_resume_strength_score(score_breakdown, role_family_buckets):
    base_score = sum(score_breakdown[name] * weight for name, weight in SCORE_WEIGHTS.items())
    support_signal = compute_support_signal(score_breakdown)
    matched_bucket_count = sum(
        1
        for bucket in role_family_buckets.values()
        if bucket["matched"] or bucket["translated"]
    )
    bucket_bonus = min(matched_bucket_count * 2.0, 8.0)
    translation_bonus = 0.0
    if (
        score_breakdown["translation_fit"] >= 80
        and score_breakdown["evidence_alignment"] >= 50
        and score_breakdown["seniority_alignment"] >= 40
        and score_breakdown["section_alignment"] >= 30
    ):
        translation_bonus = 12.0
    elif (
        score_breakdown["translation_fit"] >= 80
        and score_breakdown["evidence_alignment"] >= 20
        and score_breakdown["skills_domain_match"] >= 30
    ):
        translation_bonus = 9.0

    # The final score is intentionally directional. It blends literal overlap with
    # broader evidence signals so translated fit is not punished as harshly as a
    # strict keyword-only ATS approximation would.
    blended_score = (base_score * 0.68) + (support_signal * 0.22) + bucket_bonus + translation_bonus
    return round(min(blended_score, 100))


def get_strength_band(score, translation_fit=0, evidence_alignment=0):
    """
    Fit bands calibrated against real ATS outcomes:
    - JPMC 66%, translation_fit 100%, evidence 61% → Under Consideration
    - WF 82%, translation_fit 100%, evidence 100% → Interview

    A high translation_fit + evidence_alignment at 60-74% indicates
    genuine fit that literal phrase matching is understating.
    """
    if score >= 75:
        return "Strong match"
    if score >= 60:
        if translation_fit >= 80 and evidence_alignment >= 50:
            return "Strong translated fit"
        return "Good match"
    if score >= 45:
        return "Moderate match"
    return "Needs stronger targeting"


def analyze_documents(resume_file, job_file, debug=False):
    resume_meta = extract_text_with_metadata(
        resume_file, allowed_extensions={"pdf", "docx", "txt"}, document_kind="resume"
    )
    job_meta = extract_text_with_metadata(
        job_file, allowed_extensions={"pdf", "docx", "txt"}, document_kind="job_description"
    )

    resume_text = resume_meta["cleaned_text"]
    job_text = job_meta["cleaned_text"]

    resume_preprocessed = preprocess_text(resume_text)
    job_preprocessed = preprocess_text(job_text)
    job_sections = split_job_description_sections(job_text)
    job_focus_text = build_job_focus_text(job_sections, job_text)
    job_focus_preprocessed = preprocess_text(job_focus_text)

    detected_sections = split_resume_sections(resume_text)
    if detected_sections:
        resume_sections = detected_sections
        section_detection = "detected"
    else:
        resume_sections = infer_resume_sections(resume_text)
        section_detection = "inferred" if resume_sections else "not_detected"

    section_scores = build_section_scores(resume_sections, section_detection, job_text, job_sections)

    resume_phrases = extract_priority_phrases(resume_preprocessed)
    job_phrases = extract_priority_phrases(job_focus_preprocessed)

    keyword_overlap = compute_overlap_percentage(
        resume_preprocessed["filtered_tokens"], job_focus_preprocessed["filtered_tokens"]
    )
    phrase_overlap = compute_phrase_overlap_with_translation(
        resume_phrases, job_phrases, resume_preprocessed["normalized_text"]
    )

    skills_domain_match = round(
        (
            compute_overlap_percentage(
                [token for token in resume_preprocessed["filtered_tokens"] if token in DOMAIN_TERMS | PLATFORM_TERMS],
                [token for token in job_focus_preprocessed["filtered_tokens"] if token in DOMAIN_TERMS | PLATFORM_TERMS],
            )
            * 0.6
        )
        + (
            compute_overlap_percentage(
                resume_phrases,
                [phrase for phrase in job_phrases if any(token in DOMAIN_TERMS | PLATFORM_TERMS for token in phrase.split())],
            )
            * 0.4
        ),
        1,
    )

    seniority_alignment = round(
        compute_overlap_percentage(
            [token for token in resume_preprocessed["filtered_tokens"] if token in SENIORITY_TERMS],
            [token for token in job_focus_preprocessed["filtered_tokens"] if token in SENIORITY_TERMS],
        ),
        1,
    )

    translation_fit = round(
        compute_translation_fit(
            resume_preprocessed["normalized_text"],
            job_phrases,
        ),
        1,
    )

    section_alignment = compute_section_alignment(
        section_scores,
        resume_preprocessed["cleaned_text"],
        job_preprocessed["cleaned_text"],
    )

    role_family_buckets = build_role_bucket_output(
        resume_preprocessed["normalized_text"],
        job_phrases,
    )
    evidence_clusters = build_evidence_clusters(
        resume_preprocessed["normalized_text"],
        job_sections,
    )
    evidence_alignment = compute_evidence_alignment(role_family_buckets, evidence_clusters)

    # Deterministic directional score:
    # phrase overlap carries the most weight, then domain/skills, then section evidence.
    # This keeps the score explainable and reduces the impact of parser noise or isolated words.
    score_breakdown = {
        "phrase_overlap": round(phrase_overlap, 1),
        "keyword_overlap": round(keyword_overlap, 1),
        "skills_domain_match": round(skills_domain_match, 1),
        "seniority_alignment": seniority_alignment,
        "section_alignment": round(section_alignment, 1),
        "translation_fit": translation_fit,
        "evidence_alignment": evidence_alignment,
    }
    relevance_score = compute_relevance_score(score_breakdown)
    resume_strength_score = compute_resume_strength_score(
        score_breakdown,
        role_family_buckets,
    )
    strength_band = get_strength_band(
        resume_strength_score,
        translation_fit=score_breakdown["translation_fit"],
        evidence_alignment=score_breakdown["evidence_alignment"],
    )
    top_skills = get_top_skills(
        job_phrases,
        resume_phrases,
        resume_preprocessed["filtered_tokens"],
        job_focus_preprocessed["filtered_tokens"],
        evidence_clusters,
    )
    missing_signal_analysis = classify_missing_signals(
        evidence_clusters,
        job_phrases,
        resume_phrases,
        resume_preprocessed["normalized_text"],
    )
    missing_terms = get_missing_terms(
        job_phrases,
        resume_phrases,
        job_focus_preprocessed["filtered_tokens"],
        resume_preprocessed["filtered_tokens"],
        evidence_clusters,
        under_labeled_terms=missing_signal_analysis.get("under_labeled"),
    )
    suggestions = build_suggestions(
        missing_terms,
        missing_signal_analysis,
        score_breakdown,
        section_scores,
        section_detection,
    )

    result = {
        "status": "scored",
        "resume_filename": resume_file.name,
        "job_filename": job_file.name,
        "resume_text": resume_text,
        "job_text": job_text,
        "resume_cleaned_text": resume_preprocessed["cleaned_text"],
        "job_cleaned_text": job_preprocessed["cleaned_text"],
        "job_focus_text": job_focus_text,
        "job_focus_cleaned_text": job_focus_preprocessed["cleaned_text"],
        "job_sections": job_sections,
        "resume_sections": resume_sections,
        "section_scores": section_scores,
        "score_breakdown": score_breakdown,
        "raid_breakdown": {
            "relevance": relevance_score,
            "alignment": score_breakdown["translation_fit"],
            "translation_score": score_breakdown["translation_fit"],
            "industry_language": score_breakdown["skills_domain_match"],
            "depth": score_breakdown["section_alignment"],
            "overall": resume_strength_score,
        },
        "match_score": resume_strength_score,
        "resume_strength_score": resume_strength_score,
        "fit_band": strength_band,
        "score_disclaimer": (
            "Resume strength score is a directional fit estimate for this role, "
            "not a literal ATS score or hiring decision."
        ),
        "top_skills": top_skills,
        "missing_keywords": missing_terms,
        "missing_signal_analysis": missing_signal_analysis,
        "key_terms_from_job_description": get_curated_job_terms(
            job_sections,
            job_phrases,
            evidence_clusters,
        ),
        "role_family_buckets": role_family_buckets,
        "evidence_clusters": evidence_clusters,
        "suggestions": suggestions,
    }

    if debug:
        result["debug"] = {
            "section_detection": section_detection,
            "detected_sections": list(resume_sections.keys()),
            "job_removed_noise_terms": job_meta["removed_noise_terms"],
            "job_removed_noise_tokens": job_preprocessed["removed_noise_tokens"],
            "job_sections": job_sections,
            "job_focus_text_preview": job_focus_text[:2000],
            "resume_removed_noise_tokens": resume_preprocessed["removed_noise_tokens"],
            "resume_phrases": resume_phrases[:20],
            "job_phrases": job_phrases[:20],
            "evidence_clusters": evidence_clusters,
            "missing_signal_analysis": missing_signal_analysis,
            "scoring_components": score_breakdown,
            "support_signal": compute_support_signal(score_breakdown),
            "fit_band": strength_band,
        }

    return result
