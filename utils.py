from io import BytesIO
import json
from pathlib import Path
import re
from datetime import datetime, timezone

import pdfplumber
from docx import Document


class UnsupportedFileTypeError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


class FileTooLargeError(ValueError):
    pass


STOP_WORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}

NOISE_TERMS = {
    "apply",
    "candidate",
    "careers",
    "click",
    "content",
    "cookie",
    "cookies",
    "corporate",
    "footer",
    "home",
    "jobs",
    "main",
    "navigation",
    "page",
    "privacy",
    "search",
    "site",
    "states",
    "terms",
    "united",
    "utm",
}

SHORT_JUNK_TOKENS = {
    "co",
    "id",
    "io",
    "jp",
    "ny",
    "pm",
    "us",
}

SECTION_PATTERNS = {
    "summary": r"(professional summary|summary|profile)",
    "skills": r"(skills|core competencies|technical skills|areas of expertise|key skills|key skills [&/] expertise|skills [&/] expertise)",
    "experience": r"(experience|professional experience|employment history|career experience)",
    "education": r"(education|certifications|licenses|training)",
}

JOB_DESCRIPTION_NOISE_PATTERNS = [
    r"https?://\S+",
    r"www\.\S+",
    r"\butm_[a-z0-9_=%\-]+",
    r"\b(skip to (main )?content|skip navigation|apply now|search jobs|job alerts|cookie preferences)\b",
    r"\b(careers|candidate experience|saved jobs|sign in|requisition id|job id)\b",
    r"\b(page \d+ of \d+|page \d+)\b",
    r"\b(united states|new york,? ny|remote within|hybrid schedule|location:?)\b",
    r"\b(equal opportunity employer|all qualified applicants|will receive consideration for employment)\b",
    r"\b(privacy policy|terms of use|cookie policy|accessibility statement)\b",
    r"\b(corporate footer|global footer|site footer)\b",
    r"\b(jpmorgan chase & co\.?|jpmorganchase|jpmc|oracle|successfactors)\b",
]

JOB_SECTION_PATTERNS = {
    "responsibilities": (
        "key responsibilities",
        "responsibilities",
        "what you'll do",
        "what you will do",
    ),
    "required_qualifications": (
        "required qualifications",
        "required qualifications, capabilities, and skills",
        "qualifications",
        "what you bring",
    ),
    "preferred_qualifications": (
        "preferred qualifications",
        "preferred qualifications, capabilities, and skills",
        "preferred skills",
        "preferred experience",
    ),
}

JOB_SECTION_STOP_LINES = {
    "about us",
    "about the team",
    "similar jobs",
    "privacy & terms",
    "privacy terms useful links",
}

RESUME_FILE_SIZE_LIMIT_MB = 50
JOB_DESCRIPTION_FILE_SIZE_LIMIT_MB = 50


def normalize_text(text):
    lowered = text.lower()
    collapsed = re.sub(r"\s+", " ", lowered)
    return collapsed.strip()


def normalize_line(text):
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed


def get_file_extension(uploaded_file):
    return Path(uploaded_file.name).suffix.lower().lstrip(".")


def bytes_to_mb(size_bytes):
    return size_bytes / (1024 * 1024)


def validate_upload_size(uploaded_file, limit_mb, label):
    file_size = getattr(uploaded_file, "size", None)
    if file_size is None:
        return
    if file_size > limit_mb * 1024 * 1024:
        actual_size = round(bytes_to_mb(file_size), 1)
        raise FileTooLargeError(
            f"{label} exceeds the {limit_mb} MB limit. Uploaded size: {actual_size} MB."
        )


def extract_text_from_docx(uploaded_file):
    uploaded_file.seek(0)
    document = Document(BytesIO(uploaded_file.read()))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    uploaded_file.seek(0)
    return "\n".join(paragraphs)


def extract_text_from_pdf(uploaded_file):
    uploaded_file.seek(0)
    text_parts = []
    with pdfplumber.open(BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            page_text = page_text.strip()
            if page_text:
                text_parts.append(page_text)
    uploaded_file.seek(0)
    return "\n".join(text_parts)


def read_text_from_upload(uploaded_file, allowed_extensions):
    extension = get_file_extension(uploaded_file)

    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise UnsupportedFileTypeError(
            f"Unsupported file type '.{extension}'. Allowed types: {allowed}."
        )

    if extension == "docx":
        return extract_text_from_docx(uploaded_file)
    if extension == "pdf":
        return extract_text_from_pdf(uploaded_file)
    raise UnsupportedFileTypeError(f"Unsupported file type '.{extension}'.")


def clean_job_description_text(text):
    cleaned = text
    removed_noise = []

    for pattern in JOB_DESCRIPTION_NOISE_PATTERNS:
        matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
        removed_noise.extend(match if isinstance(match, str) else " ".join(match) for match in matches)
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    cleaned_lines = []
    for raw_line in cleaned.splitlines():
        line = normalize_line(raw_line)
        lowered = line.lower()
        if not line:
            continue
        if len(line) < 3:
            removed_noise.append(line)
            continue
        if lowered.startswith("http"):
            removed_noise.append(line)
            continue
        if re.fullmatch(r"[\W\d_]+", line):
            removed_noise.append(line)
            continue
        if any(term == lowered for term in {"careers", "apply now", "skip to content", "page"}):
            removed_noise.append(line)
            continue
        cleaned_lines.append(line)

    collapsed = "\n".join(cleaned_lines)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed).strip()
    return collapsed, sorted({item.strip().lower() for item in removed_noise if item and item.strip()})


def split_job_description_sections(text):
    lines = [normalize_line(line) for line in text.splitlines() if normalize_line(line)]
    sections = {
        "title": "",
        "responsibilities": "",
        "required_qualifications": "",
        "preferred_qualifications": "",
    }

    title_candidates = [
        line
        for line in lines[:10]
        if not re.fullmatch(r"(job information|job description|about us|about the team)", line.lower())
        and not re.match(r"\d{1,2}/\d{1,2}/\d{2,4}", line)
        and " page" not in line.lower()
        and re.search(r"[a-zA-Z]", line)
        and not re.search(r"view more jobs", line.lower())
        and len(line.split()) >= 3
        and len(line) <= 120
    ]
    if title_candidates:
        ranked_titles = sorted(
            title_candidates,
            key=lambda line: (
                not any(term in line.lower() for term in ("executive", "director", "manager", "chief", "vice president")),
                len(line),
            ),
        )
        sections["title"] = ranked_titles[0]

    section_markers = []
    for index, line in enumerate(lines):
        lowered = line.lower().rstrip(":")
        for section_name, patterns in JOB_SECTION_PATTERNS.items():
            if any(lowered == pattern or lowered.startswith(f"{pattern}:") for pattern in patterns):
                section_markers.append((index, section_name))
                break

    for marker_index, (start, section_name) in enumerate(section_markers):
        end = section_markers[marker_index + 1][0] if marker_index + 1 < len(section_markers) else len(lines)
        body_lines = []
        for line in lines[start + 1 : end]:
            lowered = line.lower().rstrip(":")
            if lowered in JOB_SECTION_STOP_LINES:
                break
            if re.match(r"\d{1,2}/\d{1,2}/\d{2,4}", line):
                continue
            if " page" in lowered and "localhost" not in lowered:
                continue
            body_lines.append(line)
        if body_lines:
            sections[section_name] = "\n".join(body_lines).strip()

    return sections


def extract_text_from_upload(uploaded_file, allowed_extensions, document_kind="generic"):
    metadata = extract_text_with_metadata(uploaded_file, allowed_extensions, document_kind)
    return metadata["cleaned_text"]


def extract_text_with_metadata(uploaded_file, allowed_extensions, document_kind="generic"):
    if document_kind == "resume":
        validate_upload_size(uploaded_file, RESUME_FILE_SIZE_LIMIT_MB, "Resume file")
    elif document_kind == "job_description":
        validate_upload_size(
            uploaded_file,
            JOB_DESCRIPTION_FILE_SIZE_LIMIT_MB,
            "Job description file",
        )

    raw_text = read_text_from_upload(uploaded_file, allowed_extensions).strip()
    if not raw_text:
        raise EmptyDocumentError(
            f"The uploaded file '{uploaded_file.name}' does not contain readable text."
        )

    cleaned_text = raw_text
    removed_noise_terms = []

    if document_kind == "job_description":
        cleaned_text, removed_noise_terms = clean_job_description_text(raw_text)
        if not cleaned_text:
            raise EmptyDocumentError(
                f"The uploaded file '{uploaded_file.name}' does not contain readable text."
            )

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "removed_noise_terms": removed_noise_terms,
    }


def append_feedback_log(log_path, payload):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def get_stop_words():
    return STOP_WORDS


def tokenize_text(text):
    return re.findall(r"[a-zA-Z][a-zA-Z&/\-]*", text)


def is_noise_token(token):
    lowered = token.lower()
    return (
        lowered in NOISE_TERMS
        or lowered in SHORT_JUNK_TOKENS
        or lowered.startswith("utm")
        or len(lowered) <= 2
    )


def preprocess_text(text):
    normalized = normalize_text(text)
    stop_words = get_stop_words()
    tokens = tokenize_text(normalized)

    filtered_tokens = []
    removed_noise_tokens = []
    for token in tokens:
        lowered = token.lower()
        normalized_token = re.sub(r"[^a-z]", "", lowered)
        if not normalized_token:
            removed_noise_tokens.append(lowered)
            continue
        if normalized_token in stop_words or is_noise_token(normalized_token):
            removed_noise_tokens.append(normalized_token)
            continue
        filtered_tokens.append(normalized_token)

    return {
        "normalized_text": normalized,
        "tokens": tokens,
        "filtered_tokens": filtered_tokens,
        "cleaned_text": " ".join(filtered_tokens),
        "removed_noise_tokens": sorted(set(removed_noise_tokens)),
    }


def split_resume_sections(text):
    lines = text.splitlines()
    positions = []
    char_index = 0

    for line in lines:
        stripped_line = normalize_line(line)
        lowered_line = stripped_line.lower()
        for name, pattern in SECTION_PATTERNS.items():
            if re.fullmatch(pattern, lowered_line):
                positions.append((char_index, name))
                break
        char_index += len(line) + 1

    positions.sort()
    sections = {}

    for index, (start, name) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(text)
        section_text = text[start:end].strip()
        if section_text:
            sections[name] = section_text

    return sections


def infer_resume_sections(text):
    lines = [normalize_line(line) for line in text.splitlines() if normalize_line(line)]
    if not lines:
        return {}

    summary_lines = lines[: min(4, len(lines))]
    skills_lines = [
        line
        for line in lines
        if "," in line
        or "|" in line
        or "/ " in line
        or re.search(r"\b(sql|oms|crm|sap|tableau|python|governance|analytics|treasury|risk)\b", line.lower())
    ][:4]
    education_lines = [
        line
        for line in lines
        if re.search(r"\b(mba|ba|bs|master|bachelor|university|college|certification|certified)\b", line.lower())
    ][:4]

    sections = {
        "summary": "\n".join(summary_lines).strip(),
        "skills": "\n".join(skills_lines).strip(),
        "experience": text.strip(),
        "education": "\n".join(education_lines).strip(),
    }
    return {name: value for name, value in sections.items() if value}
