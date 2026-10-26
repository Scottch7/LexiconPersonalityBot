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

from config import TEAMMATE_NAMES
from survey_logic import (PILOT, build_items, load_bank, make_row, participants, profile_csv,
                          read_saved, resume_position, rounds_of, shown_message, to_csv)

SJSU_BLUE = "#0055A2"
SJSU_GOLD = "#E5A823"
SENDER_RE = re.compile(r"^([^\s:]{1,20}):\s(.*)$", re.S)

CSS = """
<style>
.ctx {font-size:13px; color:#6B7280; margin:4px 0 6px 2px;}
.sender {font-size:12.5px; font-weight:700; color:#4A5568; margin:0 0 3px 6px;}
.bubble {display:inline-block; max-width:88%; background:#E9EEF5; color:#1C2B39; padding:10px 14px;
         border-radius:18px 18px 18px 4px; font-size:16px; line-height:1.35; margin-bottom:6px;}
.task {background:#FFF6E0; border-left:4px solid #E5A823; padding:10px 14px; border-radius:8px;
       font-size:16px; margin:4px 0 8px;}
.reg {font-size:13px; color:#0055A2; font-weight:600; margin-bottom:4px;}
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


def start_person(bank, person, rows=None):
    items = build_items(bank, person)
    rows = rows or []
    ss().update(person=person, plan_items=items, rows=rows, pos=resume_position(items, rows),
                session_id=uuid.uuid4().hex[:8], shown_for=None)
    if ss().pos >= len(items):
        ss().stage = "finished" if person == PILOT else "profile"
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


def screen_item(bank):
    items, pos = ss().plan_items, ss().pos
    item = items[pos]
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
        st.markdown(f'<div class="reg">{html.escape(post["instructions"][item["register"]])}</div>', unsafe_allow_html=True)
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

        with st.expander("Optional: 3 quick questions about this reply"):
            aq = {q["key"]: q for q in post["after_each_answer"]}
            rating = st.radio(aq["self_rating"]["q"], [1, 2, 3, 4, 5], index=None, horizontal=True, key=f"rate_{pos}")
            soft = st.radio(aq["softened"]["q"], ["yes", "no"], index=None, horizontal=True, key=f"soft_{pos}")
            sarc = st.radio(aq["is_sarcastic"]["q"], ["yes", "no"], index=None, horizontal=True, key=f"sarc_{pos}")

        sent = st.form_submit_button("Send", type="primary")

    if sent:
        if not abstain and not reply.strip():
            st.error("Type a reply, or tick \"I wouldn't reply\".")
            return
        if is_free and not abstain and self_label is None:
            st.error("Pick which best describes what you did.")
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
        c1, c2 = st.columns(2)
        if c1.button(f"Continue to round {ss().finished_round + 1}", type="secondary"):
            ss().stage = "item"
            st.rerun()
        c2.caption("Need a break? Close the page. Next time, choose \"Resume from a saved file\" and upload your newest CSV.")


def screen_profile(bank):
    st.subheader("Last step: how you usually text")
    st.caption("8 quick questions, asked once. Skip any you like.")
    with st.form("profile", border=False):
        answers = {}
        for q in bank["profile"]:
            if q["type"] == "choice":
                answers[q["key"]] = st.radio(q["q"], q["options"], index=None, key=f"pr_{q['key']}")
            else:
                answers[q["key"]] = st.text_input(q["q"], key=f"pr_{q['key']}")
        if st.form_submit_button("Finish", type="primary"):
            ss().profile_answers = {k: (v or "") for k, v in answers.items()}
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
