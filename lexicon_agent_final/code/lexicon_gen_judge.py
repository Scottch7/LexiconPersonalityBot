"""Generation + LLM-judge module for the Lexicon personalized reply agent.

Import from the notebook:
    from lexicon_gen_judge import *
    client = OpenAI()   # reads OPENAI_API_KEY from env; never print it

Implements generation_prompt_and_judge_rubric.md:
  - style card built from DATABASE rows only (never test rows)
  - style-only generation prompt, condition = which blocks are filled
  - 4-gram copy check + banned stock phrases -> regenerate once, logged
  - judge A (style, blind pairwise, both orders), judge B (meaning, pointwise)
  - calibration (real vs plain must win >= 85%) and paired bootstrap CI
"""
from __future__ import annotations

import json
import random
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field

DEFAULT_MODEL = "gpt-4o-mini"
GEN_TEMPERATURE = 0.7
GEN_MAX_TOKENS = 30          # P1 median reply ~3 words; 80 invites essays
JUDGE_TEMPERATURE = 0.0

BANNED_PHRASES = [
    "thanks for the invite", "i appreciate", "no worries at all", "let me know if",
    "i'd be happy to", "absolutely", "sounds great", "i understand", "feel free",
    "hope you", "just wanted to", "i totally", "that being said", "as an ai",
]

# ---------------------------------------------------------------- text utils
_WORD = re.compile(r"[a-z0-9']+")
_EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
_EMOTICON = re.compile(r"[:;=]-?[)(DPp/]|<3|\bxd\b", re.I)


def words(text: str) -> list[str]:
    return _WORD.findall(str(text).lower())


def ngrams(text: str, n: int = 4) -> set[tuple]:
    w = words(text)
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def copy_hits(text: str, sources: list[str], n: int = 4) -> list[str]:
    """Return the n-gram phrases `text` shares with any source."""
    mine = ngrams(text, n)
    hits = set()
    for s in sources:
        hits |= mine & ngrams(s, n)
    return [" ".join(h) for h in sorted(hits)]


def banned_hits(text: str, banned: list[str] = BANNED_PHRASES) -> list[str]:
    t = " ".join(words(text))
    return [b for b in banned if " ".join(words(b)) in t]


# ---------------------------------------------------------------- style card
def build_style_card(replies: list[str], negatives_note: str = "",
                     never_says: list[str] | None = None,
                     sarcastic_flags: list | None = None) -> str:
    """Compact attribute card (~60-100 tokens) from DATABASE replies only."""
    reps = [str(r) for r in replies if isinstance(r, str) and r.strip()]
    if not reps:
        raise ValueError("no replies to build a style card from")
    lens = [len(r.split()) for r in reps]
    stripped = [r.strip() for r in reps]
    pct = lambda k: round(100 * k / len(reps))
    upper = sum(s[0].isupper() for s in stripped if s[0].isalpha())
    alpha_start = sum(s[0].isalpha() for s in stripped) or 1
    no_final = sum(s[-1] not in ".!?" for s in stripped)
    space_q = sum(" ?" in r for r in reps)
    ell = sum("..." in r for r in reps)
    excl = sum("!" in r for r in reps)
    contr = sum("'" in r or "\u2019" in r for r in reps)
    emoji = sum(bool(_EMOJI.search(r)) for r in reps)
    elong = sum(bool(re.search(r"([a-z])\1\1", r.lower())) for r in reps)
    vocab = Counter(w for r in reps for w in set(words(r)))
    markers = [w for w, c in vocab.most_common(40)
               if w in {"lol", "lmao", "ngl", "bet", "yup", "yep", "nah", "ok", "okay",
                        "sure", "k", "haha", "omg", "bro", "tbh", "idk", "yeah", "yes"}][:6]
    lines = [
        f"length: median {int(statistics.median(lens))} words (range {min(lens)}-{max(lens)})",
        f"casing: capitalised first letter {round(100*upper/alpha_start)}%; no final punctuation {pct(no_final)}%",
        f"punctuation: '!' {pct(excl)}%, '...' {pct(ell)}%, space before '?' {pct(space_q)}%",
        f"contractions: {pct(contr)}% of replies",
        f"elongated words (yesss): {pct(elong)}%",
        f"emoji: {'none' if emoji == 0 else f'{pct(emoji)}%'}",
    ]
    emot = [m.group(0) for r in reps for m in _EMOTICON.finditer(r)]
    if emot:
        top = ", ".join(f'"{e}"' for e, _ in Counter(emot).most_common(3))
        lines.append(f"text emoticons: {top} in {pct(sum(bool(_EMOTICON.search(r)) for r in reps))}% of replies")
    if sarcastic_flags:
        f = [str(x).lower() in ("yes", "true", "1") for x in sarcastic_flags]
        if f:
            lines.append(f"sarcasm/teasing: self-marked on {round(100*sum(f)/len(f))}% of replies, "
                         "including ordinary messages")
    if markers:
        lines.append("frequent words: " + ", ".join(f'"{m}"' for m in markers))
    if negatives_note:
        lines.append(f"negatives: {negatives_note}")
    if never_says:
        lines.append("never says: " + ", ".join(f'"{p}"' for p in never_says))
    return "\n".join(lines)


# ---------------------------------------------------------------- generation
SYSTEM_GEN = (
    "You write a single chat reply as {person_id}, a real person.\n"
    "CONTENT comes only from INTENDED MEANING. Do not add facts, plans, names, or reasons that are not in it.\n"
    "STYLE comes from the STYLE CARD and the STYLE REFERENCES.\n"
    "STYLE REFERENCES are past replies to OTHER messages. Use them only for tone, length, casing, punctuation, "
    "word choice and how this person softens or sharpens things. Never reuse their wording, topics, or facts. "
    "Do not copy any phrase of 4 or more words from them.\n"
    "Match the card's length and casing exactly, even if that looks blunt or unpolished.\n"
    "Output only the reply text. No quotes, no explanation."
)


@dataclass
class Ref:
    incoming: str
    reply: str
    label: str = ""
    sender_role: str = ""
    stakes: str = ""


def build_gen_messages(person_id: str, intended_meaning: str, incoming: str,
                       sender: str = "Friend", context: str = "",
                       style_card: str | None = None, refs: list[Ref] | None = None) -> list[dict]:
    parts = []
    if style_card:
        parts += ["STYLE CARD", style_card, ""]
    if refs:
        parts.append("STYLE REFERENCES (style only, do not reuse wording or facts)")
        for i, r in enumerate(refs, 1):
            tag = " | ".join(x for x in (r.label, r.sender_role, r.stakes) if x)
            parts.append(f'{i}. [{tag}] "{r.incoming}" -> "{r.reply}"' if tag
                         else f'{i}. "{r.incoming}" -> "{r.reply}"')
        parts.append("")
    parts += ["MESSAGE"]
    if context:
        parts.append(f"Context: {context}")
    parts += [f"{sender}: {incoming}", "",
              "INTENDED MEANING (the only source of content)", intended_meaning, "",
              f"Write {person_id}'s reply."]
    return [{"role": "system", "content": SYSTEM_GEN.format(person_id=person_id)},
            {"role": "user", "content": "\n".join(parts)}]


@dataclass
class GenResult:
    reply: str
    attempts: int
    copy_hits: list[str] = field(default_factory=list)
    banned_hits: list[str] = field(default_factory=list)
    first_try: str = ""
    usage_tokens: int = 0


def _chat(client, messages, model, temperature, max_tokens, json_mode=False, seed=None):
    kw = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if json_mode:
        kw["response_format"] = {"type": "json_object"}
    if seed is not None:
        kw["seed"] = seed
    r = client.chat.completions.create(**kw)
    used = getattr(getattr(r, "usage", None), "total_tokens", 0) or 0
    return r.choices[0].message.content.strip(), used


def _clean(text: str) -> str:
    t = text.strip().strip('"').strip("\u201c\u201d").strip()
    return re.sub(r"^(p[12]|reply)\s*:\s*", "", t, flags=re.I)


def generate_reply(client, person_id, intended_meaning, incoming, sender="Friend", context="",
                   style_card=None, refs=None, copy_sources=None, model=DEFAULT_MODEL,
                   max_tokens=GEN_MAX_TOKENS, seed=1) -> GenResult:
    """One sample; regenerate once on a 4-gram copy or banned phrase. Final hits are logged, not hidden."""
    msgs = build_gen_messages(person_id, intended_meaning, incoming, sender, context, style_card, refs)
    sources = list(copy_sources or []) + [r.reply for r in (refs or [])] + [intended_meaning]
    tokens = 0
    text, u = _chat(client, msgs, model, GEN_TEMPERATURE, max_tokens, seed=seed); tokens += u
    text = _clean(text)
    first = text
    ch, bh = copy_hits(text, sources), banned_hits(text)
    attempts = 1
    if ch or bh:
        fix = "Rewrite it. " + (f"Do not use these copied phrases: {ch}. " if ch else "") + \
              (f"Do not use these phrases: {bh}. " if bh else "")
        msgs2 = msgs + [{"role": "assistant", "content": text}, {"role": "user", "content": fix}]
        text, u = _chat(client, msgs2, model, GEN_TEMPERATURE, max_tokens, seed=seed + 1); tokens += u
        text = _clean(text)
        ch, bh = copy_hits(text, sources), banned_hits(text)
        attempts = 2
    return GenResult(text, attempts, ch, bh, first, tokens)


# ---------------------------------------------------------------- judges
STYLE_JUDGE = (
    "You compare two candidate replies to the REFERENCE reply written by one person.\n"
    "Judge ONLY writing style: length, casing, punctuation, word choice, slang, directness, "
    "how they soften or push back.\n"
    "Ignore which one has better content, grammar, or politeness. A messier reply can be the better style match.\n"
    'REFERENCE (the person\'s real reply): "{real}"\n'
    "Also typical of this person: {typical}\n"
    'Candidate A: "{a}"\n'
    'Candidate B: "{b}"\n'
    'Answer JSON: {{"winner": "A"|"B"|"tie", "reason": "<= 20 words"}}'
)

MEANING_JUDGE = (
    'INTENDED MEANING: "{meaning}"\n'
    'MESSAGE it replies to: "{incoming}"\n'
    'REPLY: "{candidate}"\n'
    "Score 1-5 how fully the REPLY conveys the intended meaning and act, and nothing contradictory.\n"
    "5 = same act and all points; 3 = same act, a point missing or added; 1 = different act.\n"
    'Answer JSON: {{"score": n, "act_matches": true|false, "added_facts": true|false}}'
)


def _json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {}


def judge_style_once(client, real, typical, a, b, model=DEFAULT_MODEL):
    p = STYLE_JUDGE.format(real=real, typical="; ".join(f'"{t}"' for t in typical), a=a, b=b)
    out, _ = _chat(client, [{"role": "user", "content": p}], model, JUDGE_TEMPERATURE, 60, json_mode=True)
    w = str(_json(out).get("winner", "tie")).strip().upper()
    return w if w in ("A", "B") else "tie"


def judge_style_pair(client, real, typical, x, y, model=DEFAULT_MODEL) -> str:
    """Blind pairwise in both orders. Returns 'x', 'y' or 'tie' (win only if consistent)."""
    r1 = judge_style_once(client, real, typical, x, y, model)   # x is A
    r2 = judge_style_once(client, real, typical, y, x, model)   # x is B
    if r1 == "A" and r2 == "B":
        return "x"
    if r1 == "B" and r2 == "A":
        return "y"
    return "tie"


def judge_meaning(client, meaning, incoming, candidate, model=DEFAULT_MODEL) -> dict:
    p = MEANING_JUDGE.format(meaning=meaning, incoming=incoming, candidate=candidate)
    out, _ = _chat(client, [{"role": "user", "content": p}], model, JUDGE_TEMPERATURE, 40, json_mode=True)
    d = _json(out)
    return {"score": int(d.get("score", 0) or 0),
            "act_matches": bool(d.get("act_matches", False)),
            "added_facts": bool(d.get("added_facts", False))}


def calibrate(client, items, model=DEFAULT_MODEL, threshold=0.85) -> dict:
    """items: list of dicts with real, typical(list), plain. Real must beat plain >= threshold."""
    res = [judge_style_pair(client, it["real"], it["typical"], it["real"], it["plain"], model) for it in items]
    rate = sum(r == "x" for r in res) / max(len(res), 1)
    return {"real_win_rate": rate, "passed": rate >= threshold, "results": res}


# ---------------------------------------------------------------- stats
def win_rate(outcomes: list[str]) -> float:
    """outcomes in {'x','y','tie'}; tie counts as half."""
    if not outcomes:
        return float("nan")
    return sum(1.0 if o == "x" else 0.5 if o == "tie" else 0.0 for o in outcomes) / len(outcomes)


def bootstrap_ci(outcomes: list[str], n_boot=2000, seed=0, alpha=0.05):
    rng = random.Random(seed)
    n = len(outcomes)
    boots = sorted(win_rate([outcomes[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    return win_rate(outcomes), boots[int(alpha / 2 * n_boot)], boots[int((1 - alpha / 2) * n_boot) - 1]


def style_win_counts(outcome: str, meaning_x: dict, meaning_y: dict, min_meaning=4) -> str:
    """Guardrail: a style win with meaning < min_meaning becomes a tie."""
    if outcome == "x" and meaning_x["score"] < min_meaning:
        return "tie"
    if outcome == "y" and meaning_y["score"] < min_meaning:
        return "tie"
    return outcome


def gist_ok(gist: str, real_reply: str) -> bool:
    """Frozen gist rule: zero 4-gram overlap with the real reply."""
    return not copy_hits(gist, [real_reply])


CONDITIONS = {
    "A_plain": dict(card=False, k=0, pool="survey"),
    "B_semantic": dict(card=True, k=3, pool="survey"),
    "C_context": dict(card=True, k=3, pool="survey", filter=True),
    "D_verified": dict(card=True, k=3, pool="survey+gpt_verified", filter=True),
    "E_styledistance": dict(card=True, k=3, pool="survey", retriever="styledistance"),
}
