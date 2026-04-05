# Resume Analyzer

Resume Analyzer is a lightweight local tool that compares a candidate resume against a job description and returns a directional resume-strength score with practical recommendations for improvement.

---

## Overview

Resume Analyzer is a fast prototype built for one clear workflow:

- the user uploads a resume file
- the user uploads a job description file
- the app extracts text from both documents locally
- the analyzer compares skills, phrases, and role language
- the user receives a resume-strength score and targeted recommendations

Version 1 is intentionally narrow. The goal is to ship a local working analyzer in roughly 2-3 hours of implementation using Streamlit, lightweight document parsing, and straightforward text matching instead of a heavy ML pipeline.

---

## Core Concept

Resume Analyzer explores a practical approach to role-targeted resume feedback for job seekers.

Instead of treating resume review as a vague writing exercise, the project treats document overlap and missing role language as the primary source of truth.

The central idea is:

`resume file + job description file -> text extraction -> phrase/skill comparison -> score + recommendations`

This allows the system to move from:

`uploaded documents -> structured analysis -> actionable improvement guidance`

---

## Why This Project Exists

Most applicants do not know why a resume feels strong but still performs poorly against a specific role. They need fast, understandable feedback tied directly to the job description, not generic resume advice.

Resume Analyzer exists to demonstrate a different posture:

- local-first and privacy-friendly
- simple enough to build and iterate quickly
- focused on useful output over perfect scoring theory
- transparent scoring inputs
- practical recommendations the user can apply immediately

---

## Goal of V1

The goal of Version 1 is to validate whether simple document overlap
analysis can provide useful resume feedback without relying on a
large language model or heavy ML pipeline.

If the output consistently highlights meaningful gaps between a
resume and a job description, the system will be considered
validated for further development.

The deeper product goal is not to simulate a black-box ATS. It is to
help a user understand how strong their resume appears for a target
role based on the evidence the analyzer can detect.

---

## Disclaimer

The score is a directional resume-strength estimate rather than a
true ATS score. Real ATS systems and recruiting workflows use
structured fields, screening questions, ranking logic, and recruiter
review. The purpose of this tool is to surface phrase, skill, and
concept alignment between a resume and a job description to guide
improvements.

---

## Use Cases

The Resume Analyzer can be used by:

- Job seekers preparing resumes for a specific role
- Career coaches performing structured resume reviews
- Recruiters checking candidate-role alignment
- Professionals experimenting with resume targeting strategies

---

## Features

- Upload a resume in `.pdf` or `.docx` format
- Upload a job description in `.pdf` or `.docx` format
- Enforce upload limits of `50 MB` for resumes and `50 MB` for job descriptions
- Extract and normalize text locally
- Compute a directional resume-strength score
- Identify top matching skills or concepts
- Flag missing keywords from the role
- Generate suggested resume improvements
- Keep all processing on the local machine for V1
- Optionally add an OpenAI interpretation layer after local scoring
- Capture lightweight local feedback for calibration after each analysis

---

## Architecture

High-level flow:

```text
+------------------+      +-------------------+      +-------------------+
| Input Layer      | ---> | Processing Layer  | ---> | Output Layer      |
| File Upload UI   |      | Text Comparison   |      | Results Panel     |
+------------------+      +-------------------+      +-------------------+
           |                           |                          |
           v                           v                          v
+------------------+      +-------------------+      +-------------------+
| Parsed Text      |      | Scoring Engine    | ---> | User Feedback     |
| Resume + JD      |      | Rules + Weights   |      | Score + Guidance  |
+------------------+      +-------------------+      +-------------------+
```

Primary layers in the current prototype:

- `app.py`: Streamlit UI and upload handling
- `utils.py`: document parsing, text cleaning, and helper functions
- `analyzer.py`: similarity scoring, keyword overlap, and recommendations
- `sample_files/`: local test resumes and job descriptions

---

## Example Workflow

1. User uploads `Resume.docx`
2. User uploads `JobDescription.pdf`
3. The system extracts text from both documents
4. The analyzer compares matched and missing terms
5. The UI returns a resume-strength estimate and recommendations

Example result:

```text
Resume Strength: 78%

Top Skills Found
- Treasury
- Custody
- Institutional clients
- Capital markets

Missing Keywords
- Aladdin
- OMS
- Portfolio analytics
- Data governance

Key Terms from Job Description
- Treasury operations
- Institutional custody
- Regulatory reporting
- Liquidity management

Suggested Improvements
- Add platform keywords
- Strengthen summary section
- Add measurable impact
```

---

## Screenshots

The repository does not include screenshots yet.

Recommended assets to add once V1 is working:

- upload screen
- completed analysis result
- example score report for a sample resume and role

---

## Quick Start

Local setup:

```bash
mkdir resume-analyzer
cd resume-analyzer
python3 -m venv .venv
source .venv/bin/activate
pip install streamlit python-docx pdfplumber scikit-learn nltk
```

Create `requirements.txt` from the installed packages:

```bash
pip freeze > requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

Open the project at:

```text
http://localhost:8501
```

Environment variables are not required for the local analyzer.

Optional OpenAI enhancement:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Or use local Streamlit secrets for a cleaner setup:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml` and set:

```toml
OPENAI_API_KEY = "your_api_key_here"
OPENAI_MODEL = "gpt-5-mini"
```

The app will read `OPENAI_API_KEY` from either the environment or
`.streamlit/secrets.toml`. The local secrets file is ignored by git.

---

## Repository Structure

```text
resume-analyzer/
  README.md
  app.py
  analyzer.py
  utils.py
  openai_enhancer.py
  job_scout.py
  requirements.txt
  .gitignore
  DEPLOY.md
  logs/
    .gitkeep
  pages/
    1_Resume_Analyzer.py
    2_Job_Scout.py
  taxonomy/
  .streamlit/
    secrets.toml.example
```

Directory summary:

- `app.py`: Streamlit Cloud entrypoint and home page
- `pages/1_Resume_Analyzer.py`: direct resume-to-job-description scoring workflow
- `pages/2_Job_Scout.py`: target-firm job-board scanner ranked by analyzer fit
- `logs/feedback_log.jsonl`: local calibration feedback records from manual review
- `analyzer.py`: deterministic scoring, phrase extraction, section-aware analysis, and recommendation assembly
- `openai_enhancer.py`: optional OpenAI interpretation layer for fit summaries and rewrite suggestions
- `job_scout.py`: public Greenhouse and Lever fetchers plus resume-to-role ranking helpers
- `taxonomy/`: local taxonomy storage; keep `taxonomy_library.json` local because it is gitignored
- `utils.py`: `.docx` and `.pdf` extraction, JD noise cleanup, token cleanup, and stop-word handling
- `.streamlit/secrets.toml.example`: example secret values for local and Streamlit Cloud deployment

Deployment notes live in `DEPLOY.md`.

---

## Domain Model

### Analysis Pipeline

The prototype uses a deterministic scoring pipeline instead of a trained ranking model. This keeps the logic transparent, lightweight, and fast to iterate.

| Layer | Name | Role | Runs |
|-------|------|------|------|
| `L0` | Input Parsing | Reads `.docx` and `.pdf` files into plain text | On upload |
| `L1` | Text Cleaning | Lowercases, tokenizes, and removes stop words | After extraction |
| `L2` | Match Scoring | Computes phrase overlap, TF-IDF similarity, section-aware fit, and weighted strength signals | After cleaning |
| `L3` | Recommendation Engine | Produces missing terms and improvement guidance | After scoring |
| `L4` | Optional OpenAI Layer | Interprets deterministic outputs into professional feedback | After scoring |

### Output Components

| Component | Type | Responsibility |
|-----------|------|----------------|
| Resume Strength | Metric | Estimates how strong the resume appears for the target role |
| Translation Score | Metric | Estimates how well the resume translates its experience into the role's target language |
| Top Skills Found | List | Highlights strongest overlaps |
| Missing Keywords | List | Shows important literal or concept-level gaps |
| Under-Labeled Signals | List | Highlights signals that are present but not expressed in the target role's language |
| Missing Signals | List | Highlights evidence the resume likely does not show clearly enough yet |
| Key Terms from Job Description | List | Highlights the most important role language |
| Suggested Improvements | Guidance | Recommends resume edits |

---

## API Surface

Version 1 does not require an external API.

If we later separate the frontend and backend, the first internal endpoints would likely look like:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze` | Upload resume and job description for analysis |
| `GET` | `/api/health` | Basic local health check |

The local app will likely run on one development port only, depending on the chosen UI framework.

---

## Operational Workflows

### Primary Workflow

The user selects two documents, waits for local parsing and comparison, and immediately receives a structured result with clear next steps.

```text
1. Upload resume
2. Upload job description
3. Extract text
4. Compare keywords and phrases
5. Return score and recommendations
```

Core reference points:

- matched keywords increase score
- missing relevant keywords reduce score
- output should be understandable without technical explanation

### Scoring Logic

The scoring model is explainable on purpose. It is designed to answer
"how strong is this resume for this role?" rather than "what would the
employer's ATS literally score?"

Primary signals:

- phrase overlap
- keyword overlap
- skills and domain alignment
- seniority and title alignment
- section-aware evidence depth
- translated-fit evidence through a small synonym map
- taxonomy-backed evidence alignment across role-family buckets
- JD-section-aware evidence weighting for responsibilities, required qualifications, and preferred qualifications
- translation quality between resume evidence and target role language

Core similarity methods:

```text
resume text + job description text
-> phrase extraction + token cleanup + section parsing
-> taxonomy-backed phrase matching + role-family evidence clustering
-> TF-IDF similarity + overlap scoring + translated-fit checks
-> weighted directional resume-strength score
```

Current score framing:

```text
deterministic component scores -> blended support signal -> rounded resume-strength estimate out of 100
```

Suggested interpretation bands:

- `75-100`: Strong match
- `60-74`: Good match
- `45-59`: Moderate match
- `0-44`: Needs stronger targeting

The score now gives additional credit when:

- translated fit is very strong
- evidence clusters align across leadership, governance, and domain buckets
- the resume shows adjacent but credible role-family evidence even without perfect 1:1 wording

Translation Score is now exposed separately so the analyzer can explain cases like:

```text
strong experience + partial language translation = solid but not perfect fit
```

That is especially useful for executive, chief-of-staff, COO, and business-manager roles where equivalent evidence is often present but expressed differently.

Evidence clusters currently include concepts like:

- business manager / chief of staff leadership
- executive communications
- governance and operating cadence
- stakeholder coordination
- KPI and status reporting
- resource and financial planning
- data / analytics / AI
- financial-services domain credibility
- transformation and execution

The analyzer now also separates:

- `under-labeled signals`: capabilities that appear to be present in translated form
- `missing signals`: capabilities that still appear materially absent or under-evidenced

### Validation Rules

#### File Constraints

- accept `.pdf` or `.docx` resumes
- accept `.pdf` or `.docx` job descriptions
- enforce a `50 MB` resume upload limit
- enforce a `50 MB` job-description upload limit
- reject unsupported file formats

#### Output Quality Rules

- always return a score
- always show matched skills
- always show missing keywords
- always show at least one improvement suggestion
- avoid misleading precision beyond whole-number percentages
- avoid presenting the score as a literal ATS decision

---

## Missing Keyword Strategy

The app should surface terms that appear meaningful in the job description but are weak or absent in the resume.

Example missing terms:

- portfolio analytics
- trading platform
- OMS
- regulatory reporting

These terms then become resume improvement suggestions, such as:

- add missing platform and tooling keywords where truthful
- strengthen the summary using role-specific terminology
- add measurable bullet points tied to relevant domain work

---

## Build Phases

### Phase 1: Project Setup

- create the `resume-analyzer` folder
- initialize the Python virtual environment
- install Streamlit and parsing dependencies
- create `app.py`, `analyzer.py`, `utils.py`, and `requirements.txt`

### Phase 2: File Extraction

- read resume text from `.docx` using `python-docx`
- read job description text from `.pdf` using `pdfplumber`
- add fallback support for `.docx` job descriptions if needed
- validate unsupported or empty uploads

### Phase 3: Text Preprocessing

- lowercase all text
- tokenize words
- remove stop words with `nltk`
- normalize punctuation and repeated whitespace

### Phase 4: Scoring Engine

- build TF-IDF vectors with `scikit-learn`
- compute cosine similarity between resume and role text
- add phrase-aware matching and translated-fit checks
- derive weighted subscores for overlap, skills, domain language, seniority, and section evidence
- convert the combined score into a rounded directional strength score

### Phase 5: Result Generation

- extract top matched keywords
- identify missing keywords from the role
- generate suggested improvements from the gaps
- present outputs in a simple, readable format

### Phase 6: Streamlit UI

- add two file upload components
- add an `Analyze` button
- show score, matched skills, missing terms, and recommendations
- handle empty states and parsing failures gracefully

### Phase 7: Test and Refine

- run analysis with sample files
- tune score weighting if results feel misleading
- improve keyword filtering to reduce noise
- calibrate against real-world outcomes where available
- capture screenshots for the README later

---

## Calibration Findings

One of the most important project findings so far came from a real JPMorgan Chase application outcome.

- A tested resume was moved to `Under Consideration` in the employer workflow.
- The analyzer still scored that same pair too low in an earlier pass.
- That gap showed that a strict overlap model was too harsh and not representative of how modern enterprise recruiting systems usually operate.

The result of that finding:

- the project now treats the score as a `resume-strength estimate`
- translated fit matters more than exact title wording
- executive support, governance, and domain credibility must carry visible weight
- parser failures and page junk should not drag the score down disproportionately

This calibration note is now part of the product methodology, not just a test anecdote.

### Taxonomy Library

The project now includes a first-pass taxonomy builder for mining real
job-description language into a reusable library.

Current source roots:

```text
/Users/guillermoravelo/Desktop/NYC - Take Over/3Q2025 - Jobs
/Users/guillermoravelo/Desktop/NYC - Take Over/4Q2025 - 1Q2026/Consulting
/Users/guillermoravelo/Desktop/NYC - Take Over/4Q2025 - 1Q2026/Financial Services
/Users/guillermoravelo/Desktop/NYC - Take Over/4Q2025 - 1Q2026/Priority Jobs
/Users/guillermoravelo/Desktop/NYC - Take Over/4Q2025 - 1Q2026/CoS
/Users/guillermoravelo/Desktop/NYC - Take Over/4Q2025 - 1Q2026/AMEX
/Users/guillermoravelo/Desktop/NYC - Take Over/4Q2025 - 1Q2026/AT&T
/Users/guillermoravelo/Desktop/NYC - Take Over/4Q2025 - 1Q2026/BlackRock
```

Current builder:

```text
scripts/build_taxonomy.py
scripts/run_benchmark.py
```

Current output:

```text
taxonomy/taxonomy_library.json
taxonomy/README.md
```

The builder currently:

- scans the Desktop jobs folder for likely JD files
- supports multiple curated Desktop source roots
- excludes obvious resumes, cover letters, prep guides, and offer/background documents
- extracts and cleans JD text
- mines recurring bigrams and trigrams
- groups terms into role-family buckets
- preserves the current seed phrase library and synonym map for comparison

This is an initial library, not a finished ontology. It is meant to give
the analyzer a more realistic employer-language backbone over time.

The first integration phase is now in place inside the analyzer:

- mined taxonomy phrases augment the hardcoded phrase library
- role-family buckets now blend seed terms with mined employer language
- an `evidence_alignment` signal contributes to the final score
- translated executive/business-manager fit can now earn additional score credit
- the JD is split into title, responsibilities, required qualifications, and preferred qualifications
- section scores can now receive credit from concept clusters rather than only literal phrase overlap

### Phase 2 Interpretation Layer

Phase 2 builds on the deterministic analyzer rather than replacing it.

The local analyzer remains responsible for:

- resume-strength scoring
- translation scoring
- JD section-aware weighting
- evidence-cluster detection
- under-labeled versus missing-signal classification

The optional OpenAI layer is responsible for:

- professional fit interpretation
- stronger explanation of translated fit
- recruiter-style rewrite suggestions
- concise rewritten summary and bullet recommendations

Phase 2 inputs now include:

- cleaned JD by section
- cleaned resume by section
- deterministic score and translation score
- evidence clusters
- missing keywords
- under-labeled signals
- missing signals

This keeps the score explainable while allowing the app to deliver more
strategic career-counselor-style guidance.

### Feedback Loop Data

The app now supports a lightweight local feedback loop after each analysis.

The current feedback capture is meant for calibration, not automatic learning.

Each saved record can include:

- resume filename
- job filename
- resume-strength score
- fit band
- role family
- user judgment about credibility
- real-world outcome if known
- short calibration notes

The log is stored locally in:

```text
logs/feedback_log.jsonl
```

This data helps answer questions like:

- which role families are consistently under-scored
- where translated fit is still being missed
- which gaps are meaningful versus noisy
- whether score bands line up with actual recruiting outcomes

---

## Current Limitations

- V1 is still a simplified deterministic analyzer, not a real employer ATS replica
- skill and phrase extraction may still miss nuanced phrasing or synonyms outside the current maps
- PDF parsing quality depends on source formatting
- scoring is directional, not authoritative
- section detection is safer than before but still sensitive to formatting edge cases

---

## Roadmap

- Continue calibrating the score against real-world recruiting outcomes
- Expand synonym handling and role-family translation maps
- Expand the benchmark pack into labeled strong, moderate, weak, and translated-fit cases
- Improve OpenAI interpretation quality without allowing it to replace the deterministic score
- Improve phrase grouping and evidence summaries
- Export results as a downloadable report

---

## License

This project is released under the MIT License. See `LICENSE` for details.
