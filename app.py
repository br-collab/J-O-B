import streamlit as st

st.set_page_config(page_title="Resume Analyzer", page_icon="📄", layout="centered")

st.title("Resume Analyzer")
st.write(
    "Use the sidebar to open the analyzer or Job Scout and run the app locally or on Streamlit Cloud."
)
st.info(
    "Start with `1 Resume Analyzer` for a direct resume-to-role comparison, then use `2 Job Scout` to scan public postings from target firms."
)
st.write("### Pages")
st.write("- 1 Resume Analyzer: upload a resume and a job description for a detailed fit analysis")
st.write("- 2 Job Scout: upload a resume and rank public job-board postings by fit score")
st.write("### Secrets")
st.write(
    "For OpenAI enhancement, add `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in `.streamlit/secrets.toml` or Streamlit Cloud secrets."
)
