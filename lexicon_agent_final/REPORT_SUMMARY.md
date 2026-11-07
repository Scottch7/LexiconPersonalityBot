# Lexicon Personality Bot: what we did (CMPE 259, Team 3)

## Goal
An agent in a Jupyter notebook that writes chat replies the way one specific person texts. It uses a personal RAG database of that person's own replies. There is no fine-tuning.

## Data
- Two focus participants, P1 and P2. Each answered a Streamlit survey: 90 chat scenes covering 20 reply intents (10 of them negative, such as refuse, push back or sarcasm), 20 "reply properly" repeats and 5 free prompts.
- Scene labels were hidden from participants and merged back afterwards by scene ID. Teammate names were replaced with "TM".
- The "reply properly" rows were dropped for both people. They came out shorter than the chat replies (P1: 1 word vs 3, P2: 3 vs 6), so they don't capture a formal register.
- **Test split:** a seeded random draw (seed 1) of 2 answered chat scenes per intent, 40 per person. It was frozen before any tagging, retrieval or augmentation. The remaining 49 (P1) and 50 (P2) replies form each person's database. A leak check verifies that no test scene is ever retrieved.

## Pipeline
1. **Tagging:** OpenAI Structured Outputs (strict JSON) tag every reply with scenario, role, stakes, intent, tone, register, length and a neutral "intended meaning". For test items, that meaning is the frozen gist given to every condition. It is checked to share no 4-word phrase with the real reply.
2. **Style card:** compact numbers built from database rows only, such as length, capitalisation, final punctuation, emoticons, sarcasm rate and phrases the person never uses.
3. **Retrieval:** MiniLM embeddings for meaning and StyleDistance for style, both running free on CPU. Each search is filtered to one person.
4. **Generation:** gpt-4o-mini with a style-only prompt. Retrieved replies are style references only. If a draft copies 4 or more words or uses a stock GPT phrase, it is regenerated once.
5. **Agent loop:** understand the intent, retrieve, draft, check (copying, length, punctuation, stock phrases), revise up to 3 times, then learn: an accepted or edited reply joins the database.
6. **Progressive augmentation (built, not run yet):** a prompt pack for free ChatGPT. The person marks each candidate confirm, edit or reject, and verified rows feed condition D.

## Conditions
A is plain GPT. B adds semantic RAG plus the style card. C is context-aware RAG (intent and role filters). D adds human-verified examples (pending). E retrieves by StyleDistance.

## Results (seed 1, 40 test items per person)
The style score comes from a blind pairwise LLM judge, run in both orders. A win counts only if both orders agree, and only if the winner's meaning score is at least 4. The score is wins plus half the ties, and 0.5 means a draw. Ranges are 95% bootstrap confidence intervals.

| Comparison | P1 | P2 |
|---|---|---|
| B vs A | 0.80 [0.71, 0.88] | 0.65 [0.56, 0.74] |
| C vs A | 0.81 [0.72, 0.89] | 0.66 [0.57, 0.75] |
| E vs A | 0.81 [0.72, 0.89] | 0.64 [0.54, 0.74] |
| C vs B | 0.53 [0.42, 0.62] | 0.59 [0.53, 0.66] |
| E vs C | 0.54 [0.45, 0.64] | 0.50 [0.40, 0.60] |

| Guardrail | A | B | C | E | Real |
|---|---|---|---|---|---|
| Words per reply (P1 / P2) | 11.5 / 12.8 | 3.7 / 5.8 | 3.4 / 6.3 | 3.5 / 5.7 | about 3 / 5–6 |
| Meaning score, 1–5 (P1 / P2) | 4.92 / 4.97 | 4.38 / 4.55 | 4.35 / 4.58 | 4.40 / 4.68 | 4.18 / 4.47 |
| Copy rate (P1 / P2) | 5% / 0% | 2% / 0% | 0% / 0% | 0% / 0% | n/a |

**Takeaways**
- Personalization clearly beats plain GPT on style for both people, and almost never loses (at most 5 losses out of 40). Meaning holds at 4.35 or above.
- The largest gain is length and tone. Plain GPT writes 11–13 words, while the personalized conditions write at the person's real length.
- Context-aware filtering is no better than semantic retrieval for P1. For P2 the gain is small but its interval excludes 0.5. StyleDistance retrieval ties with context-aware retrieval.
- **TF-IDF person classifier (P1 vs P2):** P1 attribution rises from 10% under plain GPT to 68–75% with RAG. For P2 it stays at 82–90% in every condition, because plain GPT's full punctuated sentences already look like P2. That makes it a weak test for P2.

## Limitations
- **Judge calibration missed its target:** the real reply beat plain GPT only 68% of the time (target 85%), with 22% ties. The judge is conservative, so the win rates above are likely underestimates. The rubric needs another iteration.
- Only seed 1 has been run, with about 50 database rows per person.
- The gists were auto-written. One P2 gist (L03_2) shares a 4-word phrase with the real reply, and all of them still need a human review.
- Condition D, seeds 2–3 and each person's own blind "sounds like me" pick are not done yet.
- P2 read the 1–5 "would you send this" scale reversed (1 means very likely). The pipeline doesn't use that column.

## Cost
All runs together cost under $0.10 on gpt-4o-mini. Every call is cached, so re-running the notebook is free.
