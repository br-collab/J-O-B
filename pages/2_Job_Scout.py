import streamlit as st

from analyzer import analyze_resume_text_against_job_text
from job_scout import TARGET_FIRMS, TARGET_TITLE_KEYWORDS, fetch_target_roles
from utils import EmptyDocumentError, FileTooLargeError, UnsupportedFileTypeError


st.set_page_config(page_title="Job Scout", page_icon="🔎", layout="centered")

st.title("Job Scout")
st.write(
    "Upload your resume to scan target firms and rank public job-board postings by analyzer fit."
)
st.caption(
    f"Tracking {len(TARGET_FIRMS)} firms and {len(TARGET_TITLE_KEYWORDS)} title keywords across Greenhouse and Lever."
)

resume_file = st.file_uploader(
    "Upload Resume (.pdf, .docx)",
    type=["pdf", "docx"],
    key="job_scout_resume",
)
minimum_score = st.slider("Minimum fit score", min_value=0, max_value=100, value=40, step=5)
max_results = st.slider("Results to show", min_value=5, max_value=25, value=10, step=5)
scan_clicked = st.button("Scan target firms", type="primary")

if scan_clicked:
    if not resume_file:
        st.error("Please upload a resume before running Job Scout.")
    else:
        try:
            with st.spinner("Fetching current postings from target firms..."):
                roles = fetch_target_roles()
        except Exception as exc:
            st.error(f"Unable to fetch target roles: {exc}")
        else:
            if not roles:
                st.warning(
                    "No matching roles were returned. A firm board handle may need updating in job_scout.py."
                )
            else:
                scored_roles = []
                scoring_error = None

                with st.spinner("Scoring roles against your resume..."):
                    for role in roles:
                        description = role.get("description", "")
                        scored_role = dict(role)

                        if not description or len(description.strip()) < 100:
                            scored_role["score"] = None
                            scored_role["fit_band"] = "Insufficient description"
                            scored_role["top_skills"] = []
                            scored_role["missing_keywords"] = []
                            scored_roles.append(scored_role)
                            continue

                        try:
                            resume_file.seek(0)
                            result = analyze_resume_text_against_job_text(
                                resume_file,
                                description,
                                job_filename=f"{role['firm']}_{role['title'][:40]}.txt",
                            )
                            scored_role["score"] = result["resume_strength_score"]
                            scored_role["fit_band"] = result["fit_band"]
                            scored_role["top_skills"] = result["top_skills"][:5]
                            scored_role["missing_keywords"] = result["missing_keywords"][:5]
                        except (
                            UnsupportedFileTypeError,
                            EmptyDocumentError,
                            FileTooLargeError,
                        ) as exc:
                            scoring_error = str(exc)
                            break
                        except Exception:
                            scored_role["score"] = None
                            scored_role["fit_band"] = "Error during scoring"
                            scored_role["top_skills"] = []
                            scored_role["missing_keywords"] = []

                        scored_roles.append(scored_role)

                if scoring_error:
                    st.error(scoring_error)
                else:
                    scored_roles.sort(key=lambda role: role["score"] or 0, reverse=True)
                    filtered_roles = [
                        role for role in scored_roles if (role["score"] or 0) >= minimum_score
                    ]

                    st.metric("Matching postings", len(filtered_roles))
                    st.caption(
                        f"{len(scored_roles)} roles matched your title filters before score filtering."
                    )

                    if not filtered_roles:
                        st.info(
                            "No roles met the minimum score filter. Lower the threshold or update target firm handles."
                        )

                    for index, role in enumerate(filtered_roles[:max_results], start=1):
                        header = f"{index}. {role['firm']} | {role['title']}"
                        with st.expander(header, expanded=index <= 3):
                            score_text = "N/A" if role["score"] is None else f"{role['score']}%"
                            st.write(f"Location: {role['location']}")
                            st.write(f"Source: {role['source']}")
                            st.write(f"Fit score: {score_text}")
                            st.write(f"Fit band: {role['fit_band']}")

                            if role.get("url"):
                                st.link_button("Open role", role["url"])

                            st.write("Top matching signals")
                            for item in role["top_skills"] or ["No strong overlap found yet."]:
                                st.write(f"- {item}")

                            st.write("Likely gaps")
                            for item in role["missing_keywords"] or ["No major keyword gaps found."]:
                                st.write(f"- {item}")
