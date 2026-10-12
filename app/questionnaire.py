"""Lexicon Personality Bot: style questionnaire (v0).

Collects how a person writes (style questions, scenario replies and extra
writing samples) and saves the answers as a JSON file on this computer.

Run from the repo root:
    streamlit run app/questionnaire.py
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import streamlit as st

from questions import FORMALITY_LABELS, MIN_SCENARIO_REPLIES, SCENARIOS, STYLE_QUESTIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
RESPONSES_DIR = REPO_ROOT / "data" / "responses"

SJSU_BLUE = "#0055A2"
SJSU_GOLD = "#E5A823"

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
WORD_RE = re.compile(r"[a-z']+")
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "at", "with", "is", "it",
    "i", "you", "we", "me", "my", "your", "our", "that", "this", "be", "are", "was", "can", "will",
    "if", "so", "do", "just", "have", "what", "about", "by", "as", "from", "it's", "i'm", "i'll",
}


def header():
    st.markdown(
        f"""
        <div style="background:{SJSU_BLUE};padding:28px 32px;border-radius:12px;margin-bottom:12px">
          <div style="color:{SJSU_GOLD};font-weight:700;font-size:14px;letter-spacing:1px">
            SJSU · CMPE 259 · TEAM 3
          </div>
          <div style="color:#FFFFFF;font-size:32px;font-weight:700;margin-top:6px">
            Lexicon Personality Bot
          </div>
          <div style="color:#DCE6F2;font-size:17px;margin-top:4px">
            Style questionnaire: help the bot learn how you write
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("Takes about 10 minutes. There are no right answers; write the way you normally would.")
    st.info("Your answers are saved only on this computer (in data/responses/) and are used only by Team 3 for this class project.")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "anonymous"


def save_response(record):
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = RESPONSES_DIR / f"{slugify(record['name'])}_{stamp}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def show_quick_stats(record):
    """A first look at the person's style, from their own writing."""
    replies = list(record["scenario_replies"].values())
    texts = replies + record["writing_samples"]
    all_text = "\n".join(texts)

    words_per_reply = sum(len(r.split()) for r in replies) / len(replies)
    emojis = len(EMOJI_RE.findall(all_text))
    exclamations = all_text.count("!")
    words = [w for w in WORD_RE.findall(all_text.lower()) if w not in STOPWORDS and len(w) > 2]
    top_words = [w for w, _ in Counter(words).most_common(5)]

    st.subheader("A first look at your style")
    col1, col2, col3 = st.columns(3)
    col1.metric("Words per reply", f"{words_per_reply:.1f}")
    col2.metric("Emojis", emojis)
    col3.metric("Exclamation points", exclamations)
    if top_words:
        st.caption("Your most-used words: " + ", ".join(top_words))


def main():
    st.set_page_config(page_title="LPB Style Questionnaire", page_icon="✍️", layout="centered")
    header()

    with st.form("questionnaire"):
        st.subheader("1. About you")
        name = st.text_input("Name or nickname *")

        st.subheader("2. Your writing style")
        formality = st.select_slider(
            "How formal is your writing?",
            options=list(FORMALITY_LABELS),
            value=3,
            format_func=lambda v: FORMALITY_LABELS[v],
        )
        style = {}
        for q in STYLE_QUESTIONS:
            style[q["key"]] = st.radio(q["label"], q["options"], index=None, horizontal=True, key=q["key"])
        go_to = st.text_input(
            "Any go-to words or phrases you use a lot? (separate with commas)",
            placeholder='e.g. sounds good, no worries, lol',
        )

        st.subheader("3. Scenario replies")
        st.caption(f"Reply the way you normally would. Answer at least {MIN_SCENARIO_REPLIES}; all 10 helps the most.")
        replies = {}
        for i, sc in enumerate(SCENARIOS, 1):
            st.markdown(f"**{i}. {sc['title']}**  \n{sc['prompt']}")
            replies[sc["key"]] = st.text_area(
                f"Reply {i}", key=f"reply_{sc['key']}", height=90,
                placeholder="Your reply...", label_visibility="collapsed",
            )

        st.subheader("4. Extra writing samples (optional)")
        samples = st.text_area(
            "Paste any texts, emails or notes you wrote. Separate samples with a blank line.",
            height=150,
        )

        consent = st.checkbox("I agree that Team 3 can use my answers for this CMPE 259 class project. *")
        submitted = st.form_submit_button("Submit answers", type="primary")

    if not submitted:
        return

    answered = {k: v.strip() for k, v in replies.items() if v.strip()}
    errors = []
    if not name.strip():
        errors.append("Please enter your name or nickname.")
    if len(answered) < MIN_SCENARIO_REPLIES:
        errors.append(f"Please answer at least {MIN_SCENARIO_REPLIES} scenario replies ({len(answered)} so far).")
    if not consent:
        errors.append("Please check the consent box to submit.")
    if errors:
        for e in errors:
            st.error(e)
        return

    record = {
        "version": 1,
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
        "name": name.strip(),
        "style": {
            "formality": formality,
            "formality_label": FORMALITY_LABELS[formality],
            **style,
            "go_to_phrases": [p.strip() for p in go_to.split(",") if p.strip()],
        },
        "scenario_replies": answered,
        "writing_samples": [s.strip() for s in re.split(r"\n\s*\n", samples) if s.strip()],
    }
    path = save_response(record)

    st.success(f"Thanks, {record['name']}! Your answers were saved to {path.relative_to(REPO_ROOT)}.")
    show_quick_stats(record)
    st.download_button(
        "Download my answers (JSON)",
        data=json.dumps(record, indent=2, ensure_ascii=False),
        file_name=path.name,
        mime="application/json",
    )


main()
