"""Lexicon Personality Bot: style questionnaire.

Each question asks for a specific kind of reply (a label, e.g. "Refuse /
Decline") in a random everyday situation. Answers are never saved on the
server: when finished, the person downloads their answers as a CSV.

Run from the repo root:
    streamlit run app/questionnaire.py
"""

import csv
import io
import random
import re
from collections import Counter
from datetime import datetime

import streamlit as st

from questions import CONTEXTS, LABELS

SJSU_BLUE = "#0055A2"
SJSU_GOLD = "#E5A823"

CSV_COLUMNS = ["participant", "submitted_at", "question", "label", "context", "message", "instruction", "response"]

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
            SJSU · CMPE 259
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
    st.write(
        f"Takes about 10 minutes. Each of the {len(LABELS)} questions puts you in an everyday situation "
        "and asks for a certain kind of reply. Write the way you normally would."
    )
    st.info("Nothing is saved on this site. Your answers stay in your browser until you download them as a CSV.")


def build_questions(seed):
    """Shuffle the labels and give each one a random context."""
    rng = random.Random(seed)
    labels = rng.sample(LABELS, len(LABELS))
    contexts = []
    while len(contexts) < len(labels):
        contexts += rng.sample(CONTEXTS, len(CONTEXTS))
    return [
        {
            "label": label["label"],
            "context": ctx["name"],
            "message": ctx["message"],
            "instruction": label["template"].replace("[topic]", ctx["topic"]),
        }
        for label, ctx in zip(labels, contexts)
    ]


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "participant"


def to_csv(rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def show_quick_stats(replies):
    """A first look at the person's style, from their own replies."""
    all_text = "\n".join(replies)
    words_per_reply = sum(len(r.split()) for r in replies) / len(replies)
    words = [w for w in WORD_RE.findall(all_text.lower()) if w not in STOPWORDS and len(w) > 2]
    top_words = [w for w, _ in Counter(words).most_common(5)]

    st.subheader("A first look at your style")
    col1, col2, col3 = st.columns(3)
    col1.metric("Words per reply", f"{words_per_reply:.1f}")
    col2.metric("Emojis", len(EMOJI_RE.findall(all_text)))
    col3.metric("Exclamation points", all_text.count("!"))
    if top_words:
        st.caption("Your most-used words: " + ", ".join(top_words))


def main():
    st.set_page_config(page_title="LPB Style Questionnaire", page_icon="✍️", layout="centered")
    header()

    if "seed" not in st.session_state:
        st.session_state.seed = random.randrange(1_000_000)

    col1, col2 = st.columns([3, 1])
    col1.caption("Want different situations? New topics shuffles them (and clears your answers).")
    if col2.button("New topics"):
        st.session_state.seed = random.randrange(1_000_000)
        st.session_state.pop("result", None)

    seed = st.session_state.seed
    questions = build_questions(seed)

    with st.form("questionnaire"):
        nickname = st.text_input("Nickname *", help="Used to name your CSV file. A nickname or first name is fine.")
        st.caption("Short answers are fine: \"got it\" or an emoji counts as a reply.")
        replies = []
        for i, q in enumerate(questions, 1):
            st.markdown(f"**{i}. {q['label']}** · {q['context']}")
            st.markdown(f"> {q['message']}")
            st.markdown(f"**Your reply should:** {q['instruction']}")
            replies.append(st.text_area(
                f"Reply {i}", key=f"reply_{seed}_{i}", height=80,
                placeholder="Your reply...", label_visibility="collapsed",
            ))

        consent = st.checkbox("I agree that my answers can be used for this CMPE 259 class project. *")
        finished = st.form_submit_button("Finish", type="primary")

    if finished:
        missing = [str(i) for i, r in enumerate(replies, 1) if not r.strip()]
        errors = []
        if not nickname.strip():
            errors.append("Please enter a nickname.")
        if missing:
            errors.append(f"Please answer every question (missing: {', '.join(missing)}).")
        if not consent:
            errors.append("Please check the consent box.")
        if errors:
            st.session_state.pop("result", None)
            for e in errors:
                st.error(e)
        else:
            now = datetime.now()
            rows = [
                {
                    "participant": nickname.strip(),
                    "submitted_at": now.isoformat(timespec="seconds"),
                    "question": i,
                    **q,
                    "response": r.strip(),
                }
                for i, (q, r) in enumerate(zip(questions, replies), 1)
            ]
            st.session_state.result = {
                "csv": to_csv(rows),
                "file_name": f"{slugify(nickname)}_{now.strftime('%Y%m%d-%H%M%S')}.csv",
                "replies": [r.strip() for r in replies],
            }

    result = st.session_state.get("result")
    if result:
        st.success("All done! Download your answers and send the CSV to the team.")
        st.download_button(
            "Download my answers (CSV)",
            data=result["csv"],
            file_name=result["file_name"],
            mime="text/csv",
            type="primary",
            on_click="ignore",
        )
        show_quick_stats(result["replies"])


main()
