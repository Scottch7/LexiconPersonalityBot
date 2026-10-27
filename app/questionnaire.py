"""Lexicon Personality Bot: style questionnaire v2.

Each person answers a fixed plan of chat scenes, "proper" repeats and free prompts
(from Phil's question bank in app/bank/). One item at a time, no going back.
Nothing is saved on the server: progress is downloaded as a CSV after every round,
and uploading that file resumes where the person left off.

Run from the repo root:
    streamlit run app/questionnaire.py
"""

import html
import re
import time
import uuid
from datetime import datetime

import streamlit as st

from config import BREAK_AFTER_ROUND, BREAK_MINUTES, PROPER_MIN_WORDS, TEAMMATE_NAMES
from survey_logic import (PILOT, break_minutes_left, build_items, load_bank, make_row, participants,
                          profile_csv, read_saved, resume_position, rounds_of, shown_message, to_csv)

SJSU_BLUE = "#0055A2"
SJSU_GOLD = "#E5A823"
SENDER_RE = re.compile(r"^([^\s:]{1,20}):\s(.*)$", re.S)
RATING_LABELS = {1: "1 No way", 2: "2", 3: "3 Maybe", 4: "4", 5: "5 Yes"}

CSS = """
<style>
.ctx {font-size:13px; color:#6B7280; margin:4px 0 6px 2px;}
.sender {font-size:12.5px; font-weight:700; color:#4A5568; margin:0 0 3px 6px;}
.bubble {display:inline-block; max-width:88%; background:#E9EEF5; color:#1C2B39; padding:10px 14px;
         border-radius:18px 18px 18px 4px; font-size:16px; line-height:1.35; margin-bottom:6px;}
.task {background:#FFF6E0; border-left:4px solid #E5A823; padding:10px 14px; border-radius:8px;
       font-size:16px; margin:4px 0 8px;}
.reg {font-size:13px; color:#0055A2; font-weight:600; margin-bottom:4px;}
.proper {background:#0055A2; color:#FFFFFF; padding:10px 14px; border-radius:8px; font-size:15px;
         font-weight:600; margin:2px 0 10px;}
</style>
"""


def header():
    st.markdown(
        f"""
        <div style="background:{SJSU_BLUE};padding:22px 26px;border-radius:12px;margin-bottom:10px">
          <div style="color:{SJSU_GOLD};font-weight:700;font-size:13px;letter-spacing:1px">SJSU · CMPE 259</div>
          <div style="color:#FFFFFF;font-size:28px;font-weight:700;margin-top:4px">Lexicon Personality Bot</div>
          <div style="color:#DCE6F2;font-size:16px;margin-top:2px">Style questionnaire v2: reply the way you really text</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def teammate_names():
    try:
        names = list(st.secrets["teammate_names"])
        if names:
            return names
    except Exception:
        pass
    return TEAMMATE_NAMES


def device():
    try:
        ua = st.context.headers.get("User-Agent", "")
    except Exception:
        return ""
    return "mobile" if re.search(r"Mobi|Android|iPhone|iPad", ua) else "desktop"


def ss():
    return st.session_state


def at_break(items, pos):
    """True when pos is the first item after the halfway-break round."""
    if pos <= 0 or pos >= len(items) or items[pos]["round"] == items[pos - 1]["round"]:
        return False
    return rounds_of(items).index(items[pos - 1]["round"]) + 1 == BREAK_AFTER_ROUND


def start_person(bank, person, rows=None):
    items = build_items(bank, person)
    rows = rows or []
    pos = resume_position(items, rows)
    ss().update(person=person, plan_items=items, rows=rows, pos=pos,
                session_id=uuid.uuid4().hex[:8], shown_for=None)
    if pos >= len(items):
        ss().stage = "finished" if person == PILOT else "profile"
    elif at_break(items, pos) and break_minutes_left(rows, BREAK_MINUTES):
        ss().stage, ss().finished_round = "round_done", BREAK_AFTER_ROUND
    else:
        ss().stage = "item"


def file_stub():
    user = "P1" if ss().person == PILOT else ss().person
    tag = "pilot" if ss().person == PILOT else "v2"
    return f"{user}_{tag}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"


# ---------------- screens ----------------

def screen_start(bank):
    st.write(
        "You'll see short messages from a group chat and reply the way you'd actually text. "
        "There are no right answers. The full survey is 10 rounds (about 115 replies), best done in two sittings of about 25 minutes."
    )
    st.info("Nothing is saved on this site. After each round you download a CSV. Keep it: uploading it later lets you pick up where you left off.")

    new_tab, resume_tab = st.tabs(["Start", "Resume from a saved file"])
    with new_tab:
        person = st.radio(
            "Who is taking it?", participants(bank), index=None, horizontal=True,
            format_func=lambda p: "Pilot (5 test scenes)" if p == PILOT else p,
        )
        if st.button("Start", type="primary", disabled=person is None):
            start_person(bank, person)
            st.rerun()
    with resume_tab:
        up = st.file_uploader("Upload the last CSV you downloaded from this app", type="csv")
        if up is not None and st.button("Resume", type="primary"):
            rows, err = read_saved(up.getvalue(), bank["columns"])
            if err:
                st.error(err)
            elif not rows:
                st.error("That file has no answers in it yet.")
            else:
                pilot = all(r.get("round") == "pilot" for r in rows)
                person = PILOT if pilot else rows[0]["user_id"]
                if not pilot and person not in bank["plan"]:
                    st.error(f"Unknown participant '{person}' in that file.")
                else:
                    start_person(bank, person, rows)
                    st.rerun()


def screen_part2_intro():
    st.subheader("Part 2: proper replies")
    st.write(
        "Nice work, the texting part is done. For the rest of the survey you'll see messages you already answered. "
        "This time, write each reply as a **proper, well-written message**, like an email to a professor or a message at work."
    )
    st.markdown("- Full sentences\n- Correct spelling, capitals and punctuation\n- No slang or abbreviations")
    st.caption("Short texts like \"sure\" or \"yesss\" don't count here. Same 3 quick questions after each reply.")
    if st.button("Got it, start Part 2", type="primary"):
        ss().part2_seen = True
        st.rerun()


def screen_item(bank):
    items, pos = ss().plan_items, ss().pos
    item = items[pos]
    if item["register"] == "survey" and not ss().get("part2_seen"):
        screen_part2_intro()
        return
    rounds = rounds_of(items)
    rnd_idx = rounds.index(item["round"]) + 1
    in_round = [i for i, it in enumerate(items) if it["round"] == item["round"]]
    k = in_round.index(pos) + 1

    if ss().shown_for != pos:  # start the timer when this item first appears
        ss().shown_for, ss().shown_at = pos, time.time()

    label = "Pilot" if ss().person == PILOT else f"Round {rnd_idx} of {len(rounds)}"
    st.caption(f"{label} · reply {k} of {len(in_round)}")
    st.progress(pos / len(items))

    msg, _ = shown_message(bank, item, ss().person, teammate_names())
    post = bank["post"]
    is_free = item["type"] == "free"

    if is_free:
        st.markdown('<div class="reg">Free reply</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="task">{html.escape(msg)}</div>', unsafe_allow_html=True)
    else:
        if item["register"] == "survey":
            st.markdown('<div class="proper">Part 2 · Proper reply: full sentences, correct spelling and punctuation</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="reg">{html.escape(post["instructions"]["chat"])}</div>', unsafe_allow_html=True)
        ctx = bank["scenes"][item["id"]]["context"]
        st.markdown(f'<div class="ctx">{html.escape(ctx)}</div>', unsafe_allow_html=True)
        m = SENDER_RE.match(msg)
        sender, text = (m.group(1), m.group(2)) if m else ("", msg)
        if sender:
            st.markdown(f'<div class="sender">{html.escape(sender)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="bubble">{html.escape(text)}</div>', unsafe_allow_html=True)

    with st.form(f"item_{pos}", clear_on_submit=False, border=False):
        if item["register"] == "survey":
            reply = st.text_area("Your reply", key=f"reply_{pos}", height=90, placeholder="Write a proper reply...")
        else:
            reply = st.text_input("Your reply", key=f"reply_{pos}", placeholder="type it like you'd text it",
                                  autocomplete="off")
        abstain = st.checkbox(post["abstain_option"], key=f"abstain_{pos}")

        self_label = None
        if is_free:
            fl = post["free_mode_self_label"]
            self_label = st.selectbox(fl["q"], fl["options"], index=None, placeholder="Pick one", key=f"label_{pos}")

        st.markdown("**3 quick questions about your reply**")
        st.caption("Required, unless you ticked \"I wouldn't reply\".")
        aq = {q["key"]: q for q in post["after_each_answer"]}
        rating = st.radio(f'{aq["self_rating"]["q"]} (1 = no way, 5 = yes, exactly as written)', [1, 2, 3, 4, 5],
                          index=None, horizontal=True, key=f"rate_{pos}", format_func=RATING_LABELS.get)
        soft = st.radio(aq["softened"]["q"], ["yes", "no"], index=None, horizontal=True, key=f"soft_{pos}")
        sarc = st.radio(aq["is_sarcastic"]["q"], ["yes", "no"], index=None, horizontal=True, key=f"sarc_{pos}")

        err = st.empty()
        sent = st.form_submit_button("Send", type="primary")

    if sent:
        if not abstain:
            if not reply.strip():
                err.error("Type a reply, or tick \"I wouldn't reply\".")
                return
            missing = [name for name, val in [("which best describes what you did", self_label if is_free else ""),
                                              ("would you send it", rating), ("did you tone it down", soft),
                                              ("sarcastic or teasing", sarc)] if val is None]
            if missing:
                err.error("Please answer: " + ", ".join(missing) + ".")
                return
            if (item["register"] == "survey" and len(reply.split()) < PROPER_MIN_WORDS
                    and ss().get("short_ok") != pos):
                ss().short_ok = pos
                err.warning("That's short for a proper reply. Try writing it as a full, polished message. "
                            "To keep it as is, press Send again.")
                return
        row = make_row(
            bank, item, pos + 1, ss().person, ss().session_id, teammate_names(), reply, abstain=abstain,
            self_rating="" if rating is None else str(rating), softened=soft or "", is_sarcastic=sarc or "",
            self_label=self_label or "", seconds=time.time() - ss().shown_at, device=device(),
        )
        ss().rows.append(row)
        ss().pos = pos + 1
        end_of_round = ss().pos >= len(items) or items[ss().pos]["round"] != item["round"]
        if end_of_round:
            ss().stage = "round_done"
            ss().finished_round = rnd_idx
        st.rerun()


def screen_round_done(bank):
    items = ss().plan_items
    rounds = rounds_of(items)
    last = ss().pos >= len(items)
    pilot = ss().person == PILOT
    done_label = "Pilot done!" if pilot else f"Round {ss().finished_round} of {len(rounds)} done!"
    st.success(done_label + " Download your progress now so nothing is lost.")
    st.download_button("Download progress (CSV)", data=to_csv(ss().rows, bank["columns"]),
                       file_name=f"{file_stub()}.csv", mime="text/csv", type="primary", on_click="ignore")
    st.caption("Each download includes everything so far, so you only need to keep the newest file.")

    if pilot:
        st.write("Thanks! Send the CSV to Phil.")
        if st.button("Done"):
            ss().stage = "finished"
            st.rerun()
    elif last:
        if st.button("Continue to the last few questions"):
            ss().stage = "profile"
            st.rerun()
    else:
        nxt = ss().finished_round + 1
        halfway = ss().finished_round == BREAK_AFTER_ROUND
        if halfway and BREAK_MINUTES:
            st.info(f"Halfway there! Take a break of at least {BREAK_MINUTES} minutes before round {nxt}. "
                    "Stretch, get some water: rested answers are better data.")
        elif halfway:
            st.info("Halfway there! This is a good time for a break.")
        c1, c2 = st.columns(2)
        go = c1.button(f"Continue to round {nxt}", type="secondary")
        c2.caption("Need a break? Close the page. Next time, choose \"Resume from a saved file\" and upload your newest CSV.")
        if go:
            left = break_minutes_left(ss().rows, BREAK_MINUTES) if halfway else 0
            if left:
                st.warning(f"Break isn't over yet. Come back in about {left} minute{'s' if left > 1 else ''}.")
            else:
                ss().stage = "item"
                st.rerun()


def screen_profile(bank):
    st.subheader("Last step: how you usually text")
    st.caption("8 quick questions, asked once. All are required; if one doesn't apply to you, write \"none\".")
    with st.form("profile", border=False):
        answers = {}
        for q in bank["profile"]:
            if q["type"] == "choice":
                answers[q["key"]] = st.radio(q["q"], q["options"], index=None, key=f"pr_{q['key']}")
            else:
                answers[q["key"]] = st.text_input(q["q"], key=f"pr_{q['key']}")
        err = st.empty()
        if st.form_submit_button("Finish", type="primary"):
            if any(v is None or not str(v).strip() for v in answers.values()):
                err.error("Please answer all 8 questions.")
                return
            ss().profile_answers = answers
            ss().stage = "finished"
            st.rerun()


def screen_finished(bank):
    rows = ss().rows
    st.success("All done, thank you! Download your files and send them to Phil.")
    st.download_button("Download all answers (CSV)", data=to_csv(rows, bank["columns"]),
                       file_name=f"{file_stub()}.csv", mime="text/csv", type="primary", on_click="ignore")
    if ss().person != PILOT and "profile_answers" in ss():
        st.download_button("Download profile answers (CSV)",
                           data=profile_csv(ss().person, ss().profile_answers, bank["profile"]),
                           file_name=f"{file_stub()}_profile.csv", mime="text/csv", on_click="ignore")
    answered = sum(r["abstain"] != "true" for r in rows)
    st.caption(f"{answered} replies, {len(rows) - answered} skipped with \"I wouldn't reply\".")


def main():
    st.set_page_config(page_title="LPB Style Questionnaire", page_icon="✍️", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    header()
    bank = load_bank()
    stage = ss().get("stage", "start")
    {"start": screen_start, "item": screen_item, "round_done": screen_round_done,
     "profile": screen_profile, "finished": screen_finished}[stage](bank)


main()
