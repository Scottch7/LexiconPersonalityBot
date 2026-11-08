"""Use the Lexicon personal style database with ChatGPT (the app) instead of the API.

Three ways, no API key needed for 1 and 2:
  1. paste_prompt()      -> a ready-to-paste prompt for chatgpt.com, with this message's retrieved examples
  2. export_custom_gpt() -> instructions + knowledge file for a Custom GPT or a ChatGPT Project
  3. (optional) the API path in lexicon_gen_judge.generate_reply, if OPENAI_API_KEY is set
Every reply you keep can be logged with log_feedback(); kept rows feed condition D / the database.
Owner: Researcher (retrieval/export). Reuses MLP Fine-tuner's prompt + style card and ProjLexicon's split files.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from lexicon_gen_judge import (SYSTEM_GEN, BANNED_PHRASES, build_gen_messages, build_style_card,
                               copy_hits, banned_hits)
from lexicon_retrieval import ExampleStore, strip_sender

ROOT = Path(__file__).resolve().parent.parent
RESPONSE_FILES = {"P1": ROOT / "data/P1_responses.csv", "P2": ROOT / "data/P2_responses.csv"}
BANK_CSV = ROOT / "data/prompt_bank_v2.csv"
LABELS = pd.read_csv(ROOT / "data/labels.csv").target_label.tolist()
INSTRUCTION_LIMIT = 8000          # Custom GPT "Instructions" box limit (characters)


# ------------------------------------------------------------------ store + card
def test_ids(uid, seed=1):
    f = ROOT / f"frozen/split_{uid}_seed{seed}.json"
    return json.loads(f.read_text())["test_scene_ids"] if f.exists() else []


def load_store(uid, exclude_test=True, extra_rows=None) -> ExampleStore:
    """exclude_test=True keeps the evaluation clean. Set False for everyday use (all replies)."""
    ex = test_ids(uid) if exclude_test else []
    return ExampleStore.from_survey(str(RESPONSE_FILES[uid]), str(BANK_CSV), exclude_scene_ids=ex,
                                    extra_rows=extra_rows)


def style_card(uid, store) -> str:
    raw = pd.read_csv(RESPONSE_FILES[uid])
    keep = raw[raw.scene_id.isin(store.df.scene_id) & (raw.register == "chat")]
    flags = keep.is_sarcastic.dropna().tolist() if "is_sarcastic" in keep else None
    return build_style_card(store.df.response.tolist(), sarcastic_flags=flags or None)


# ------------------------------------------------------------------ 1. paste prompt
def paste_prompt(uid, store, incoming, intended_meaning, context="", sender="TM", k=5,
                 condition="C_context", label=None, n_options=1):
    """Returns (prompt_text, refs). Paste prompt_text into chatgpt.com as one message."""
    refs = store.retrieve(condition, uid, incoming, k=k, context=context,
                          intended_meaning=intended_meaning, label=label)
    msgs = build_gen_messages(uid, intended_meaning, strip_sender(incoming), sender, context, style_card(uid, store), refs)
    rules = msgs[0]["content"]
    if n_options > 1:
        rules = rules.replace("Output only the reply text.",
                              f"Output {n_options} different candidate replies, one per line, numbered.")
    text = "INSTRUCTIONS\n" + rules + "\n\n" + msgs[1]["content"]
    return text, refs


# ------------------------------------------------------------------ check + learn
def check_reply(uid, store, reply, refs=()):
    """Local checks on whatever ChatGPT gave back (free)."""
    lens = store.df.response.str.split().str.len()
    w = len(str(reply).split())
    lo, hi = int(lens.quantile(0.1)), int(lens.quantile(0.9))
    return {"words": w, "typical_range": f"{lo}-{hi}", "length_ok": lo <= w <= max(hi, lo + 1),
            "copied_4grams": copy_hits(reply, [r.reply for r in refs]),
            "stock_phrases": banned_hits(reply)}


def log_feedback(uid, incoming, intended_meaning, gpt_reply, final_reply, context="", label="",
                 path=None):
    """Keep a reply. origin = gpt_confirmed if unchanged, gpt_edited if you rewrote it."""
    path = Path(path or ROOT / f"augment/app_feedback_{uid}.csv")
    path.parent.mkdir(exist_ok=True)
    row = {"user_id": uid, "scene_id": f"APP_{dt.datetime.now():%Y%m%d%H%M%S}", "register": "chat",
           "incoming": incoming, "response": final_reply.strip(), "target_label": label,
           "sender_role": "", "stakes": "", "context": context,
           "origin": "gpt_confirmed" if final_reply.strip() == gpt_reply.strip() else "gpt_edited",
           "gpt_reply": gpt_reply, "intent_gist": intended_meaning,
           "timestamp": dt.datetime.now().isoformat(timespec="seconds")}
    new = not path.exists()
    with path.open("a", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(row))
        if new:
            wr.writeheader()
        wr.writerow(row)
    return row


def feedback_rows(uid):
    """Logged rows in the shape ExampleStore(extra_rows=...) expects."""
    p = ROOT / f"augment/app_feedback_{uid}.csv"
    return pd.read_csv(p) if p.exists() else None


# ------------------------------------------------------------------ 2. Custom GPT / Project export
def export_custom_gpt(uid, store, out_dir=None):
    out = Path(out_dir or ROOT / "chatgpt_export")
    out.mkdir(exist_ok=True)
    card = style_card(uid, store)
    instructions = f"""You are {uid}'s reply writer. You draft ONE chat reply that sounds exactly like {uid} texting.

HOW THE USER TALKS TO YOU
The user sends:
  Message: <what the other person wrote>
  Meaning: <what {uid} wants to say back>      (required; this is the ONLY source of content)
  Context: <optional: who it is, situation>
  Intent:  <optional, one of: {", ".join(LABELS)}>
If Meaning is missing, ask for it in one short line. Do not guess it.

STEPS (do them silently)
1. Search the knowledge file {uid}_examples.md for 3-5 past replies with the same intent and a similar situation.
   They show HOW {uid} writes. They are NOT content: never reuse their wording, topics, or facts,
   and never copy any phrase of 4+ words from them.
2. Write the reply: content only from Meaning; style from the STYLE CARD and the examples.
3. Check before answering: length inside {uid}'s range, casing and final punctuation match the card,
   no added facts, none of these stock phrases: {", ".join(BANNED_PHRASES)}.
   If a check fails, rewrite (up to 3 times).

OUTPUT
Only the reply text. No quotes, no explanation, no alternatives unless the user asks for options.
If the user says "options", give 3 numbered candidates.
If the user edits your reply, treat their edit as the better example of {uid}'s style for the rest of the chat.

STYLE CARD ({uid}, measured from their real replies)
{card}

GENERAL RULE
{SYSTEM_GEN.format(person_id=uid)}
"""
    assert len(instructions) <= INSTRUCTION_LIMIT, len(instructions)
    lines = [f"# {uid} past replies (style examples only, grouped by intent)", ""]
    for lab, g in store.df.groupby("target_label"):
        lines += [f"## Intent: {lab}", ""]
        for r in g.itertuples():
            meta = ", ".join(str(x) for x in (r.sender_role, r.stakes) if isinstance(x, str) and x)
            lines += [f"- Situation: {r.context}" if isinstance(r.context, str) and r.context else "- Situation: (none)",
                      f"  From ({meta or 'friend'}): {r.incoming}",
                      f"  {uid} replied: {r.response}", ""]
    (out / f"instructions_{uid}.md").write_text(instructions)
    (out / f"{uid}_examples.md").write_text("\n".join(lines))
    return out / f"instructions_{uid}.md", out / f"{uid}_examples.md", len(instructions), len(store.df)
