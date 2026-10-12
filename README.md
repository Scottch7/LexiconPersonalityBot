# Lexicon Personality Bot

CMPE 259 (SJSU) · Team 3. A bot that learns how a person writes (their go-to words, phrases, tone and structure) and drafts new text in their voice.

## Style questionnaire (v0)

A Streamlit form that collects:

1. Name or nickname
2. Writing style questions (formality, tone, emojis, greetings, sign-offs, structure)
3. Replies to 10 everyday scenarios (same prompts for everyone, so we can compare styles)
4. Extra writing samples (optional)

Answers are saved as one JSON file per submission in `data/responses/`. That folder is git-ignored, so answers stay on your computer and never get pushed.

### Run it

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/questionnaire.py
```

Then open http://localhost:8501 in your browser. The app runs only while that terminal is open; press Ctrl+C to stop it.

### Change the questions

Edit `app/questions.py`. The style questions, the 10 scenarios and the minimum number of replies all live there.

## Project layout

```
app/
  questionnaire.py   Streamlit questionnaire
  questions.py       Questions and scenarios
data/responses/      Saved answers (git-ignored)
.streamlit/          Theme (SJSU colors)
```
