# Summit Line Construction — Project Intelligence Platform

AI-powered project management demo for Summit Line Construction (a Quanta Services company).

## Features
- **PM Intelligence Feed** — Portfolio KPIs, project cards, AI Monday morning briefing
- **Portfolio Risk Dashboard** — Plotly charts: burn %, planned vs actual, risk quadrant scatter
- **Process Automation Designer** — AI designs specific automation solutions for each project's manual Excel workflows
- **Field → Leadership Report** — Paste raw field notes, get a structured leadership report
- **AI Project Assistant** — Full chat interface with streaming responses and complete portfolio context

## Local Setup

```bash
pip install -r requirements.txt
mkdir -p .streamlit
echo 'ANTHROPIC_API_KEY = "your_key_here"' > .streamlit/secrets.toml
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push this folder to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and set `app.py` as the main file
4. Add secret: `ANTHROPIC_API_KEY = your_key_here`
5. Deploy

## Tech Stack
- **Frontend:** Streamlit
- **AI:** Anthropic Claude (`claude-sonnet-4-20250514`)
- **Charts:** Plotly
- **Data:** Synthetically generated with Faker (seeded, reproducible)
