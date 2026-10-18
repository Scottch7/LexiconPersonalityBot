# Lexicon Personality Bot

CMPE 259 (SJSU). A bot that learns how a person writes (their go-to words, phrases, tone and structure) and drafts new text in their voice.

## Style questionnaire

A Streamlit form where each question asks for a specific kind of reply (a **label**, e.g. "Refuse / Decline" or "Acknowledge") in a random everyday situation (a **context**, e.g. a restaurant plan or a group project).

- Every label is asked once, in a shuffled order, each with a random context.
- **New topics** reshuffles the situations (and clears the answers).
- Short replies count: "got it" or an emoji is a valid answer.
- **Nothing is saved on the server.** When finished, the person downloads their answers as a CSV and sends it to the team.

### CSV format

One row per question:

| Column | Meaning |
| --- | --- |
| `participant` | Nickname the person entered |
| `submitted_at` | When they finished |
| `question` | Question number (1 = first shown) |
| `label` | Reply type, e.g. `Refuse / Decline` |
| `context` | Situation, e.g. `Restaurant` |
| `message` | What was said to them |
| `instruction` | What their reply should do |
| `response` | Their reply |

### Change the labels or situations

Edit `app/questions.py`: `LABELS` holds the reply types (with a `[topic]` placeholder) and `CONTEXTS` holds the situations.

### Run it locally

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/questionnaire.py
```

Then open http://localhost:8501 in your browser. The app runs only while that terminal is open; press Ctrl+C to stop it.

### Deploy (Streamlit Community Cloud)

1. Sign in at https://share.streamlit.io with GitHub (give it access to this repository only).
2. **Create app** with repository `Scottch7/LexiconPersonalityBot`, branch `main`, main file `app/questionnaire.py`, and pick an app URL.
3. Check the app's **Sharing** settings so teammates can open it.

Every push to `main` redeploys the app automatically.

## Project layout

```
app/
  questionnaire.py   Streamlit questionnaire
  questions.py       Labels and situations
.streamlit/          Theme (SJSU colors) and settings
```
