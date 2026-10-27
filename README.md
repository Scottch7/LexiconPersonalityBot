# Lexicon Personality Bot

CMPE 259 (SJSU). A personalized writing agent that learns how one person writes and drafts chat replies in their voice, using personalized RAG and human feedback.

## Style questionnaire v2

A Streamlit app that collects each focus person's replies to a fixed plan of group-chat messages, from the question bank in `app/bank/`.

- **Who:** pick **P1**, **P2** or **Pilot** (5 test scenes) on the start screen. No names appear on the site.
- **What:** 10 rounds, 115 items: 90 chat scenes (20 reply types), 20 "proper" repeats of earlier scenes and 5 free prompts, then 8 profile questions. Best done in two sittings of about 25 minutes.
- **How it feels:** one message at a time in a chat bubble, one reply box, an "I wouldn't reply" option and 3 required follow-up questions (1 to 5 "would you send this", toned down, sarcastic). No going back to earlier answers.
- **Every question is required.** The only way past an item without answering is "I wouldn't reply", which saves the row with an empty reply and no follow-ups. The 8 profile questions are required too.
- **Halfway break:** after round 5 the person must wait 10 minutes before round 6 (also checked when resuming from a CSV).
- **Part 2, proper replies:** before the first "proper" item an intro screen explains the switch, and each proper item shows a blue banner. A proper reply under 4 words gets one nudge to write more; pressing Send again keeps it.
- **Nothing is saved on the server.** After every round the person downloads a CSV of everything so far. To continue later, choose **Resume from a saved file** and upload the newest CSV.
- **Exact text:** replies are saved exactly as typed (no trimming or case changes), with seconds to answer.

### Output files

- **Answers CSV:** one row per item, using the columns in `app/bank/response_schema.csv`. `target_label` and `split` are left empty on purpose; they are filled in later by joining on `scene_id`. `edited_count` is empty because Streamlit cannot count backspaces.
- **Profile CSV:** one row per person with the 8 texting-habit answers.

### Settings

`app/config.py` holds the teammate names that fill `{TM}` in messages, the pilot scenes, who each participant is (so nobody sees their own name), the halfway break (`BREAK_AFTER_ROUND`, `BREAK_MINUTES`; set minutes to 0 to only suggest a break) and the proper-reply length nudge (`PROPER_MIN_WORDS`). Names can also be set in Streamlit secrets as `teammate_names = [...]`.

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

The app is deployed from branch `main`, main file `app/questionnaire.py`. Every push to `main` redeploys it automatically.

## Project layout

```
app/
  questionnaire.py   Streamlit screens (v2)
  survey_logic.py    Item order, output rows, CSV save and resume
  config.py          Teammate names, pilot scenes, participants
  bank/              Question bank (blind version: no labels or test split)
data/
  seeds/             Questionnaire v1 answers
  generated/         Generated datasets
.streamlit/          Theme (SJSU colors) and settings
```
