"""
pages/2_Job_Scout.py

Job Scout tab — fetches open roles from target firms, scores them
against your uploaded resume, and surfaces the best fits.
"""

import streamlit as st
from job_scout import fetch_target_roles, score_roles_against_resume, TARGET_FIRMS, TARGET_TITLE_KEYWORDS

st.set_page_config(page_title="Job Scout", page_icon="🔍", layout="centered")

st.title("Job Scout")
st.write(
    "Upload your resume and scan open roles across your target firms. "
    "Each role is scored against your resume using the same analyzer."
)

# ---------------------------------------------------------------------------
# Sidebar: show target firms and title keywords for transparency
# ---------------------------------------------------------------------------
with st.sidebar:
    st.write("### Target Firms")
    for firm in TARGET_FIRMS:
        st.write(f"- {firm['name']}")

    st.write("### Title Keywords")
    for kw in TARGET_TITLE_KEYWORDS:
        st.write(f"- {kw}")
    st.caption("Edit these in job_scout.py to refine your search.")

# ---------------------------------------------------------------------------
# Resume upload — check session state and disk store first
# ---------------------------------------------------------------------------
from session_store import load_resume as _load_resume
session_resume = st.session_state.get("resume_file") or _load_resume()
if session_resume:
    st.session_state["resume_file"] = session_resume
if session_resume:
    st.success(f"Using resume from analyzer session: **{session_resume.name}**")
    resume_file = session_resume
else:
    resume_file = st.file_uploader(
        "Upload your resume (.pdf or .docx)",
        type=["pdf", "docx"],
        key="scout_resume",
    )
    if resume_file:
        st.session_state["resume_file"] = resume_file

score_toggle = st.checkbox(
    "Score each role against my resume",
    value=True,
    help="Uncheck to just browse open roles without running the analyzer.",
)

run_scout = st.button(
    "Run Job Scout",
    type="primary",
    disabled=(not resume_file and score_toggle),
)

if not resume_file and score_toggle:
    st.info("Upload your resume above to enable scoring, or uncheck scoring to browse roles only.")

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
if run_scout:
    with st.spinner("Polling job boards across target firms..."):
        roles = fetch_target_roles()

    if not roles:
        st.warning(
            "No matching roles found right now. "
            "Firms may not be actively posting on Greenhouse or Lever, "
            "or the board handles need updating in job_scout.py."
        )
        st.stop()

    st.success(f"Found {len(roles)} matching role{'s' if len(roles) != 1 else ''} across target firms.")

    if score_toggle and resume_file:
        with st.spinner(f"Scoring {len(roles)} roles against your resume..."):
            roles = score_roles_against_resume(roles, resume_file)
        st.caption("Roles sorted by fit score (highest first).")
    else:
        st.caption("Showing roles without scoring.")

    # ---------------------------------------------------------------------------
    # Display results
    # ---------------------------------------------------------------------------
    for role in roles:
        score = role.get("score")
        fit_band = role.get("fit_band", "")
        score_label = f"{score}% — {fit_band}" if score is not None else fit_band or "Not scored"

        with st.expander(f"**{role['firm']}** · {role['title']} · {role['location']}"):
            if score is not None:
                st.metric("Resume Strength", f"{score}%")
                st.caption(fit_band)
            else:
                st.caption(score_label)

            if role.get("top_skills"):
                st.write("**Top Skills Found**")
                for skill in role["top_skills"]:
                    st.write(f"- {skill}")

            if role.get("missing_keywords"):
                st.write("**Missing Keywords**")
                for kw in role["missing_keywords"]:
                    st.write(f"- {kw}")

            if role.get("url"):
                st.markdown(f"[View full job posting →]({role['url']})")

            if not score_toggle:
                preview = role.get("description", "")[:500]
                if preview:
                    st.caption(preview + "...")
