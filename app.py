from pathlib import Path

import streamlit as st

from analyzer import analyze_documents
from openai_enhancer import enhance_analysis_with_openai, has_openai_api_key
from utils import (
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    append_feedback_log,
)


st.set_page_config(page_title="Resume Analyzer", page_icon="📄", layout="centered")

FEEDBACK_LOG_PATH = Path(__file__).resolve().parent / "logs" / "feedback_log.jsonl"
OPENAI_ERROR_LOG_PATH = Path(__file__).resolve().parent / "logs" / "openai_error.log"

st.markdown(
    """
    <style>
    [data-testid="stFileUploaderDropzoneInstructions"] small {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Resume Analyzer")
st.write(
    "Upload a resume and a job description to estimate resume strength for a target role."
)

resume_file = st.file_uploader(
    "Upload Resume (.pdf, .docx)",
    type=["pdf", "docx"],
    key="resume",
)
job_file = st.file_uploader(
    "Upload Job Description (.pdf, .docx)",
    type=["pdf", "docx"],
    key="job",
)

if resume_file is not None:
    st.session_state["resume_file"] = resume_file
if job_file is not None:
    st.session_state["job_file"] = job_file

resume_file = st.session_state.get("resume_file")
job_file = st.session_state.get("job_file")

analyze_clicked = st.button("Analyze", type="primary")
use_openai_enhancement = st.checkbox(
    "Use OpenAI enhancement",
    value=False,
    disabled=not has_openai_api_key(),
    help="Requires OPENAI_API_KEY in your environment.",
)
show_debug_details = st.checkbox("Show debug details", value=False)

if analyze_clicked:
    if not resume_file or not job_file:
        st.error("Please upload both a resume and a job description.")
    else:
        try:
            result = analyze_documents(resume_file, job_file, debug=show_debug_details)
        except (UnsupportedFileTypeError, EmptyDocumentError, FileTooLargeError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unable to parse uploaded files: {exc}")
        else:
            st.session_state["analysis_result"] = result
            st.success("Documents parsed, preprocessed, and scored successfully.")
            raid_breakdown = result["raid_breakdown"]
            section_scores = result["section_scores"]
            enhanced = None

            st.metric("Resume Strength", f"{result['resume_strength_score']}%")
            st.caption(result["fit_band"])
            st.caption(result["score_disclaimer"])

            st.write("### Strength Breakdown")
            st.write(f"Relevance: {raid_breakdown['relevance']}%")
            st.write(f"Translation Score: {raid_breakdown['translation_score']}%")
            st.write(f"Alignment: {raid_breakdown['alignment']}%")
            st.write(f"Industry Language: {raid_breakdown['industry_language']}%")
            st.write(f"Depth: {raid_breakdown['depth']}%")

            st.write("### Section Breakdown")
            for label, key in (
                ("Summary", "summary"),
                ("Skills", "skills"),
                ("Experience", "experience"),
                ("Education/Certifications", "education"),
            ):
                value = section_scores.get(key)
                if value is None:
                    st.write(f"{label}: section not clearly detected")
                else:
                    st.write(f"{label}: {value}%")

            st.write("### Top Skills Found")
            for skill in result["top_skills"] or ["No strong overlap found yet."]:
                st.write(f"- {skill}")

            st.write("### Missing Keywords")
            for keyword in result["missing_keywords"] or ["No major keyword gaps found."]:
                st.write(f"- {keyword}")

            missing_signal_analysis = result.get("missing_signal_analysis", {})
            if missing_signal_analysis.get("under_labeled"):
                st.write("### Under-Labeled Signals")
                for item in missing_signal_analysis["under_labeled"]:
                    st.write(f"- {item}")

            if missing_signal_analysis.get("missing"):
                st.write("### Missing Signals")
                for item in missing_signal_analysis["missing"]:
                    st.write(f"- {item}")

            st.write("### Key Terms from Job Description")
            for term in result["key_terms_from_job_description"] or ["No key role language extracted."]:
                st.write(f"- {term}")

            st.write("### Suggested Improvements")
            for suggestion in result["suggestions"]:
                st.write(f"- {suggestion}")

            if use_openai_enhancement:
                st.write("### OpenAI Enhancement")
                status_placeholder = st.empty()
                try:
                    with st.spinner("Running OpenAI enhancement..."):
                        status_placeholder.info(
                            "Calling GPT-5 mini to interpret fit, translated signals, and rewrite opportunities."
                        )
                        enhanced = enhance_analysis_with_openai(result)
                except Exception as exc:
                    status_placeholder.empty()
                    append_feedback_log(
                        OPENAI_ERROR_LOG_PATH,
                        {
                            "resume_filename": result["resume_filename"],
                            "job_filename": result["job_filename"],
                            "error": str(exc),
                        },
                    )
                    st.error(f"OpenAI enhancement failed: {exc}")
                else:
                    status_placeholder.success("OpenAI interpretation completed.")
                    st.write("### OpenAI Fit Summary")
                    st.write(enhanced["fit_summary"])

                    if enhanced.get("confidence_note"):
                        st.caption(enhanced["confidence_note"])

                    st.write("### Strongest Alignments")
                    for item in enhanced["strongest_alignments"]:
                        st.write(f"- {item}")

                    st.write("### Realistic Missing Signals")
                    for item in enhanced["missing_signals"]:
                        st.write(f"- {item}")

                    st.write("### Recommended Resume Edits")
                    for item in enhanced["recommended_edits"]:
                        st.write(f"- {item}")

                    st.write("### Optional Rewritten Summary")
                    st.write(enhanced["rewritten_summary"])

                    st.write("### Optional Suggested Bullets")
                    for item in enhanced["suggested_bullets"]:
                        st.write(f"- {item}")

            st.write("### Feedback Loop")
            with st.form("feedback_form"):
                role_family = st.selectbox(
                    "Role family",
                    [
                        "Executive / Chief of Staff / Business Manager",
                        "Financial Services / Markets / Treasury",
                        "Consulting / Strategy / Transformation",
                        "Data / Analytics / AI",
                        "Other",
                    ],
                )
                user_judgment = st.selectbox(
                    "Did this result feel credible?",
                    [
                        "Yes, mostly credible",
                        "Partly credible",
                        "No, score felt too low",
                        "No, score felt too high",
                    ],
                )
                real_world_outcome = st.selectbox(
                    "Real-world outcome, if known",
                    [
                        "Unknown",
                        "No response yet",
                        "Under review / under consideration",
                        "Interview",
                        "Rejected",
                    ],
                )
                notes = st.text_area(
                    "Notes",
                    placeholder="Optional calibration notes about what matched, what was missed, or what felt off.",
                )
                feedback_submitted = st.form_submit_button("Save feedback")

            if feedback_submitted:
                append_feedback_log(
                    FEEDBACK_LOG_PATH,
                    {
                        "resume_filename": result["resume_filename"],
                        "job_filename": result["job_filename"],
                        "resume_strength_score": result["resume_strength_score"],
                        "fit_band": result["fit_band"],
                        "role_family": role_family,
                        "user_judgment": user_judgment,
                        "real_world_outcome": real_world_outcome,
                        "top_skills": result["top_skills"],
                        "missing_keywords": result["missing_keywords"],
                        "notes": notes.strip(),
                        "openai_used": bool(use_openai_enhancement),
                        "openai_completed": bool(enhanced),
                    },
                )
                st.success("Feedback saved to the local calibration log.")

            if show_debug_details and "debug" in result:
                st.write("### Debug Details")
                st.json(result["debug"])
