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

## Results (seed 1, 40 test items per person, style judge v2)
The style score comes from a pairwise LLM judge (gpt-4o). It sees the person's style card and 8 of their real replies, and must pick A or B. We read the probability of each answer and average it over both orders, which cancels the judge's habit of favoring whichever reply comes first. A pair is a tie only if that average is within 0.05 of 0.5, or if the style winner's meaning score is below 4. The score is wins plus half the ties, so 0.5 means a draw. Ranges are 95% bootstrap confidence intervals. All conditions are scored on the same frozen seed-1 replies.

| Comparison | P1 | P2 |
|---|---|---|
| B vs A | 0.90 [0.84, 0.96] (32 / 8 / 0) | 0.84 [0.74, 0.93] (30 / 7 / 3) |
| C vs A | 0.90 [0.84, 0.96] (32 / 8 / 0) | 0.89 [0.80, 0.96] (33 / 5 / 2) |
| E vs A | 0.91 [0.85, 0.96] (33 / 7 / 0) | 0.89 [0.80, 0.96] (34 / 3 / 3) |
| C vs B | 0.56 [0.44, 0.69] (14 / 17 / 9) | 0.51 [0.39, 0.62] (13 / 15 / 12) |
| E vs C | 0.41 [0.31, 0.51] (6 / 21 / 13) | 0.53 [0.40, 0.65] (15 / 12 / 13) |

Counts are wins / ties / losses out of 40.

*v1 judge, same replies, for reference:* P1 B 0.80, C 0.81, E 0.81 vs A, C vs B 0.53, E vs C 0.54; P2 B 0.65, C 0.66, E 0.64 vs A, C vs B 0.59, E vs C 0.50. v1 called 51% of all pairs ties; v2 calls 26% ties (12% from the judge itself, the rest from the meaning rule).

| Guardrail | A | B | C | E | Real |
|---|---|---|---|---|---|
| Words per reply (P1 / P2) | 11.5 / 12.8 | 3.7 / 5.8 | 3.4 / 6.3 | 3.5 / 5.7 | about 3 / 5–6 |
| Meaning score, 1–5 (P1 / P2) | 4.92 / 4.97 | 4.38 / 4.55 | 4.35 / 4.58 | 4.40 / 4.68 | 4.18 / 4.47 |
| Copy rate (P1 / P2) | 5% / 0% | 2% / 0% | 0% / 0% | 0% / 0% | n/a |

**Takeaways**
- Personalization clearly beats plain GPT on style for both people: 0.84 to 0.91, with every interval well above 0.5 and at most 3 losses out of 40. Meaning holds at 4.35 or above.
- The largest gain is length and tone. Plain GPT writes 11–13 words, while the personalized conditions write at the person's real length.
- The three retrieval methods are not clearly different. C vs B is a draw for both people. E vs C leans toward C for P1 (0.41), but its interval reaches 0.51, so it is not conclusive. The small P2 C vs B edge seen with the v1 judge did not hold up.
- **TF-IDF person classifier (P1 vs P2):** P1 attribution rises from 10% under plain GPT to 68–75% with RAG. For P2 it stays at 82–90% in every condition, because plain GPT's full punctuated sentences already look like P2. That makes it a weak test for P2.

## Limitations
- **Judge calibration now passes:** we tested the judge on 60 database replies that are not in the test set (30 per person), split into a tune half and a check half, and froze it on the tune half, where its one change (gpt-4o-mini to gpt-4o) was chosen. On the check half the real reply beat plain GPT in 28 of 30 pairs (93%, target 85%), with 2 ties and 0 losses, and on the original 40 test pairs it now wins 37 (v1: 27).
- The judge is still an LLM. It sees the person's real reply for each test item, and gpt-4o-mini wrote the replies, so some model bias may remain. The blind "sounds like me" pick by each person is the real check.
- Only seed 1 has been run, with about 50 database rows per person, and five comparisons were made without a multiple-comparison correction.
- The gists were auto-written. One P2 gist (L03_2) shares a 4-word phrase with the real reply, and all of them still need a human review.
- Condition D, seeds 2–3 and each person's own blind "sounds like me" pick are not done yet.
- P2 read the 1–5 "would you send this" scale reversed (1 means very likely). The pipeline doesn't use that column.

## Cost
The v2 judge run cost $0.82 (830 gpt-4o calls). All runs together, including generation and testing, cost under $1.00. Every call is cached, so re-running the notebook is free.
