# Deployment Guide

## Step 1 — Assemble the repo locally

Your final folder structure should look like this:

```
resume-analyzer/
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
    (empty for now — add taxonomy_library.json locally, it is gitignored)
  .streamlit/
    secrets.toml.example
```

Copy all files above into a single folder on your machine.
Do NOT commit `.streamlit/secrets.toml` — it is in `.gitignore`.

---

## Step 2 — Create the GitHub repo

1. Go to https://github.com/new
2. Name it `resume-analyzer` (private recommended)
3. Do NOT initialize with a README — you are pushing existing code
4. Click **Create repository**

---

## Step 3 — Push from your terminal

```bash
cd resume-analyzer
git init
git add .
git commit -m "Initial commit — Resume Analyzer + Job Scout"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/resume-analyzer.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## Step 4 — Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click **New app**
3. Select your `resume-analyzer` repo
4. Set **Main file path** to `app.py`
5. Click **Advanced settings** → **Secrets**
6. Paste your secrets in TOML format:

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-5-mini"
```

7. Click **Deploy**

Streamlit Cloud installs from `requirements.txt` automatically.
The Job Scout tab appears in the sidebar as **2 Job Scout**.

---

## Step 5 — Verify Job Scout firm handles

After deploying, run Job Scout with your resume.
If a firm returns zero results, its Greenhouse or Lever board handle
may differ from the one in `job_scout.py`.

To find the correct handle:
- Greenhouse: visit the firm's careers page, look for `boards.greenhouse.io/<handle>`
- Lever: visit the firm's careers page, look for `jobs.lever.co/<handle>`

Update `TARGET_FIRMS` in `job_scout.py` and push. Streamlit Cloud redeploys automatically.

---

## Future — adding Claude Code to your workflow

Once the repo is live, Claude Code (VS Code extension or terminal) can:
- Run the app locally with `streamlit run app.py`
- Edit `job_scout.py` to add firms or title keywords
- Expand the analyzer scoring logic in `analyzer.py`
- Add a third Streamlit page for feedback log review

Install: https://claude.ai/code
