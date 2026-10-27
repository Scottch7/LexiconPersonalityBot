"""Questionnaire v2 logic: loading the bank, building each person's item list,
making output rows and resuming from a saved CSV. No Streamlit code here."""

import csv
import io
import json
import math
import random
from datetime import datetime
from pathlib import Path

from config import ORIGIN, PARTICIPANT_NAMES, PILOT_SCENES, SOURCE

BANK = Path(__file__).resolve().parent / "bank"
PILOT = "Pilot"


def load_json(name):
    return json.loads((BANK / name).read_text(encoding="utf-8"))


def load_bank():
    scenes = {s["scene_id"]: s["shown"] for s in load_json("scenes.json")}
    return {
        "scenes": scenes,
        "free": {f["free_id"]: f["prompt"] for f in load_json("free_prompts.json")},
        "plan": load_json("round_plan.json"),
        "post": load_json("post_questions.json"),
        "profile": load_json("profile_questions.json"),
        "columns": (BANK / "response_schema.csv").read_text(encoding="utf-8").strip().split(","),
    }


def participants(bank):
    return [*bank["plan"].keys(), PILOT]


def build_items(bank, person):
    """Flat, ordered list of items for one person. Each item knows its round."""
    if person == PILOT:
        return [{"round": "pilot", "type": "scene", "id": sid, "register": "chat"} for sid in PILOT_SCENES]
    items = []
    for rnd in bank["plan"][person]:
        for it in rnd["items"]:
            items.append({"round": rnd["round"], "type": it["type"], "id": it["id"], "register": it["register"]})
    return items


def rounds_of(items):
    seen = []
    for it in items:
        if it["round"] not in seen:
            seen.append(it["round"])
    return seen


def teammate_for(person, scene_id, names):
    """Same teammate every time for this person and scene (seeded), never the person's own name."""
    own = PARTICIPANT_NAMES.get("P1" if person == PILOT else person, "")
    pool = [n for n in names if n.lower() != own.lower()] or names
    return random.Random(f"{person}:{scene_id}").choice(pool)


def shown_message(bank, item, person, names):
    """Returns (message text, teammate name used or "")."""
    if item["type"] == "free":
        return bank["free"][item["id"]], ""
    msg = bank["scenes"][item["id"]]["incoming_message"]
    if "{TM}" in msg:
        tm = teammate_for(person, item["id"], names)
        return msg.replace("{TM}", tm), tm
    return msg, ""


def item_key(item_type, item_id, register):
    return f"{item_type}:{item_id}:{register}"


def make_row(bank, item, order, person, session_id, names, response, abstain=False,
             self_rating="", softened="", is_sarcastic="", self_label="", seconds=None, device=""):
    """One output row. The response is saved exactly as typed (no strip, no case changes).
    A skipped item ("I wouldn't reply") keeps no reply, follow-ups or self label."""
    msg, tm = shown_message(bank, item, person, names)
    is_free = item["type"] == "free"
    if abstain:
        response = self_rating = softened = is_sarcastic = self_label = ""
    row = {c: "" for c in bank["columns"]}
    row.update({
        "user_id": "P1" if person == PILOT else person,
        "session_id": session_id,
        "round": item["round"],
        "item_order": order,
        "item_type": item["type"],
        "scene_id": "" if is_free else item["id"],
        "free_id": item["id"] if is_free else "",
        "register": item["register"],
        "target_label": "",   # filled in later by joining on scene_id
        "split": "",          # chosen at random after collection
        "shown_message": msg,
        "teammate_filled": tm,
        "response": response,
        "abstain": "true" if abstain else "false",
        "self_rating": self_rating,
        "softened": softened,
        "is_sarcastic": is_sarcastic,
        "self_label": self_label if is_free else "",
        "is_free_reply": "true" if is_free else "false",
        "seconds_to_answer": "" if seconds is None else f"{seconds:.1f}",
        "edited_count": "",   # Streamlit cannot count backspaces
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": SOURCE,
        "origin": ORIGIN,
        "intent_gist": "",
        "device": device,
    })
    return row


def to_csv(rows, columns):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def read_saved(file_bytes, columns):
    """Parse a previously downloaded CSV. Returns (rows, error message or None)."""
    try:
        text = file_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        missing = [c for c in ("user_id", "item_type", "scene_id", "free_id", "register") if c not in (reader.fieldnames or [])]
        if missing:
            return [], "This doesn't look like a questionnaire file (missing " + ", ".join(missing) + ")."
        rows = [{c: r.get(c, "") for c in columns} for r in reader]
        return rows, None
    except UnicodeDecodeError:
        return [], "Couldn't read that file. Upload the CSV you downloaded from this app."


def resume_position(items, rows):
    """Index of the first item in plan order that has no saved row."""
    done = {item_key(r["item_type"], r["scene_id"] or r["free_id"], r["register"]) for r in rows}
    for i, it in enumerate(items):
        if item_key(it["type"], it["id"], it["register"]) not in done:
            return i
    return len(items)


def break_minutes_left(rows, minutes, now=None):
    """Minutes of the halfway break still to wait, counted from the last saved answer.
    A timestamp in the future (CSV saved on a machine with another clock) counts as a finished break."""
    if not rows or minutes <= 0:
        return 0
    try:
        last = datetime.fromisoformat(rows[-1]["timestamp"])
    except (KeyError, ValueError):
        return 0
    waited = ((now or datetime.now()) - last).total_seconds() / 60
    return 0 if waited < 0 else max(0, math.ceil(minutes - waited))


def profile_csv(person, answers, profile_questions):
    cols = ["user_id", "timestamp"] + [q["key"] for q in profile_questions]
    row = {"user_id": "P1" if person == PILOT else person, "timestamp": datetime.now().isoformat(timespec="seconds")}
    row.update({q["key"]: answers.get(q["key"], "") for q in profile_questions})
    return to_csv([row], cols)
