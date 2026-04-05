"""
pages/3_Resume_Rewriter.py

Resume Rewriter tab.
- Runs after the analyzer has scored a resume + JD pair.
- Sends original resume text + analyzer findings to OpenAI.
- Shows side-by-side: original vs rewritten, section by section.
- User accepts, rejects, or gives feedback on each section.
- Iterates until satisfied, then scores the rewrite automatically.
"""

from io import BytesIO
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Resume Rewriter", page_icon="✍️", layout="wide")

st.title("Resume Rewriter")
st.write(
    "Run the Resume Analyzer first, then come here to generate a targeted rewrite "
    "grounded strictly in your actual experience."
)

# ---------------------------------------------------------------------------
# Gate: require analyzer result in session state
# ---------------------------------------------------------------------------
result = st.session_state.get("analysis_result")
resume_file = st.session_state.get("resume_file")

if not result:
    st.warning(
        "No analysis found in this session. Go to **Resume Analyzer**, "
        "upload your resume and a job description, click **Analyze**, "
        "then return here. Note: refreshing the page clears session data — "
        "keep the analyzer tab open in the same browser session."
    )
    if st.button("Go to Resume Analyzer"):
        st.switch_page("app.py")
    st.stop()

resume_text = result.get("resume_text", "")
job_title = result.get("job_sections", {}).get("title", "Target Role")
current_score = result.get("resume_strength_score", 0)

st.info(
    f"Loaded analysis for **{result.get('resume_filename', 'your resume')}** "
    f"vs **{result.get('job_filename', 'job description')}** — "
    f"current score: **{current_score}%**"
)

# ---------------------------------------------------------------------------
# OpenAI key check
# ---------------------------------------------------------------------------
try:
    import streamlit as st_check
    openai_key = st_check.secrets.get("OPENAI_API_KEY", "")
except Exception:
    import os
    openai_key = os.getenv("OPENAI_API_KEY", "")

if not openai_key:
    st.error("OpenAI API key not found. Add it in Streamlit Cloud → Settings → Secrets.")
    st.stop()

# ---------------------------------------------------------------------------
# Generate or iterate rewrite
# ---------------------------------------------------------------------------
from resume_rewriter import rewrite_resume
from analyzer import analyze_documents

draft_key = "rewrite_draft"
feedback_key = "rewrite_feedback"

if draft_key not in st.session_state:
    st.session_state[draft_key] = None
if feedback_key not in st.session_state:
    st.session_state[feedback_key] = {}

col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Original")
with col_right:
    st.subheader("Rewritten")

# ---------------------------------------------------------------------------
# Generate button
# ---------------------------------------------------------------------------
user_feedback_input = st.text_area(
    "Feedback for next draft (optional — leave blank for first run)",
    placeholder="e.g. Make the summary shorter. Keep the Army bullet exactly as written. "
                "The Computershare role needs stronger outcome language.",
    height=80,
    key="feedback_input",
)

generate_label = "Generate Rewrite" if not st.session_state[draft_key] else "Regenerate with Feedback"
if st.button(generate_label, type="primary"):
    with st.spinner("Rewriting resume — grounded strictly to your original experience..."):
        try:
            draft = rewrite_resume(
                resume_text=resume_text,
                analysis_result=result,
                user_feedback=user_feedback_input,
            )
            st.session_state[draft_key] = draft
        except Exception as exc:
            st.error(f"Rewrite failed: {exc}")
            st.stop()

draft = st.session_state[draft_key]

if not draft:
    st.caption("Click **Generate Rewrite** to produce the first draft.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary section
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### Professional Summary")
col_left, col_right = st.columns(2)

original_summary = ""
resume_lines = resume_text.splitlines()
for i, line in enumerate(resume_lines):
    if "summary" in line.lower() or "profile" in line.lower():
        original_summary = "\n".join(resume_lines[i+1:i+6]).strip()
        break
if not original_summary:
    original_summary = "\n".join(resume_lines[:4]).strip()

with col_left:
    st.text_area("Original summary", value=original_summary, height=140, disabled=True, key="orig_summary")

with col_right:
    edited_summary = st.text_area(
        "Rewritten summary (edit freely)",
        value=draft.get("summary", ""),
        height=140,
        key="edit_summary",
    )

# ---------------------------------------------------------------------------
# Experience sections
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### Experience")

experience_drafts = draft.get("experience", [])
edited_bullets = {}

for i, role_draft in enumerate(experience_drafts):
    role_label = f"{role_draft.get('role', '')} — {role_draft.get('firm', '')} ({role_draft.get('dates', '')})"
    st.markdown(f"**{role_label}**")

    col_left, col_right = st.columns(2)

    # Find original bullets for this role from resume text
    original_block = ""
    firm = role_draft.get("firm", "").lower()
    for j, line in enumerate(resume_lines):
        if firm and firm[:8] in line.lower():
            original_block = "\n".join(resume_lines[j:j+8]).strip()
            break

    with col_left:
        st.text_area(
            "Original",
            value=original_block or "(see original resume)",
            height=160,
            disabled=True,
            key=f"orig_role_{i}",
        )

    with col_right:
        bullets_text = "\n".join(f"• {b}" for b in role_draft.get("bullets", []))
        edited = st.text_area(
            "Rewritten (edit freely)",
            value=bullets_text,
            height=160,
            key=f"edit_role_{i}",
        )
        edited_bullets[i] = edited

# ---------------------------------------------------------------------------
# Skills section
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### Skills")
col_left, col_right = st.columns(2)

original_skills = ""
for j, line in enumerate(resume_lines):
    if "skill" in line.lower() or "expertise" in line.lower() or "competenc" in line.lower():
        original_skills = "\n".join(resume_lines[j:j+6]).strip()
        break

with col_left:
    st.text_area("Original skills", value=original_skills or "(see original resume)", height=120, disabled=True, key="orig_skills")

with col_right:
    edited_skills = st.text_area(
        "Rewritten skills (edit freely)",
        value=draft.get("skills", ""),
        height=120,
        key="edit_skills",
    )

# ---------------------------------------------------------------------------
# Grounding notes — transparency on what was reframed and why
# ---------------------------------------------------------------------------
st.divider()
with st.expander("Grounding notes — what was reframed and why"):
    notes = draft.get("grounding_notes", [])
    if notes:
        for note in notes:
            st.write(f"- {note}")
    else:
        st.write("No grounding notes returned.")

# ---------------------------------------------------------------------------
# Re-score the rewrite
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### Score the Rewrite")
st.caption(
    "Assemble your edited sections into a single text block and score it against the same JD "
    "to see the new estimate."
)

if st.button("Score Rewritten Resume", type="secondary"):
    assembled_parts = [edited_summary, ""]

    for i, role_draft in enumerate(experience_drafts):
        assembled_parts.append(
            f"{role_draft.get('role', '')} | {role_draft.get('firm', '')} | {role_draft.get('dates', '')}"
        )
        bullets_raw = edited_bullets.get(i, "")
        for line in bullets_raw.splitlines():
            clean = line.strip().lstrip("•").strip()
            if clean:
                assembled_parts.append(f"• {clean}")
        assembled_parts.append("")

    assembled_parts.append("KEY SKILLS & EXPERTISE")
    assembled_parts.append(edited_skills)

    assembled_text = "\n".join(assembled_parts)

    class _FakeFile:
        def __init__(self, name, content):
            self.name = name
            self._buf = BytesIO(content.encode("utf-8"))
            self.size = len(content.encode("utf-8"))

        def read(self):
            return self._buf.read()

        def seek(self, p):
            return self._buf.seek(p)

    class _FakePDFFile:
        """Wraps the original resume bytes so the scorer can re-read it."""

        def __init__(self, original_file):
            self.name = original_file.name
            original_file.seek(0)
            self._data = original_file.read()
            self.size = len(self._data)
            self._buf = BytesIO(self._data)

        def read(self):
            return self._buf.read()

        def seek(self, p):
            return self._buf.seek(p)

    with st.spinner("Scoring rewritten resume..."):
        try:
            jd_fake = _FakeFile(
                name=result.get("job_filename", "jd.txt"),
                content=result.get("job_text", ""),
            )
            resume_fake = _FakeFile(
                name="rewritten_resume.txt",
                content=assembled_text,
            )
            # Score rewritten text vs original JD text
            rescore = analyze_documents(resume_fake, jd_fake)
            new_score = rescore["resume_strength_score"]
            delta = new_score - current_score

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Original Score", f"{current_score}%")
            with col2:
                st.metric("Rewritten Score", f"{new_score}%", delta=f"{delta:+}%")
            with col3:
                st.metric("Fit Band", rescore["fit_band"])

            if new_score >= 90:
                st.success("Target reached. Resume is strongly aligned with the role.")
            elif new_score >= 80:
                st.info("Strong improvement. Review grounding notes and refine further if needed.")
            else:
                st.warning(
                    "Score improved but still below 90%. Review the missing keywords section "
                    "and add feedback above, then regenerate."
                )

            st.write("**Remaining missing keywords:**")
            for kw in rescore.get("missing_keywords", []):
                st.write(f"- {kw}")

        except Exception as exc:
            st.error(f"Scoring failed: {exc}")

# ---------------------------------------------------------------------------
# Download rewritten resume as plain text
# ---------------------------------------------------------------------------
st.divider()
assembled_download = "\n\n".join([
    edited_summary,
    *[
        f"{experience_drafts[i].get('role', '')} | {experience_drafts[i].get('firm', '')} | {experience_drafts[i].get('dates', '')}\n" +
        edited_bullets.get(i, "")
        for i in range(len(experience_drafts))
    ],
    "KEY SKILLS & EXPERTISE\n" + edited_skills,
])

st.download_button(
    label="Download Rewritten Resume (txt)",
    data=assembled_download,
    file_name="rewritten_resume.txt",
    mime="text/plain",
)
