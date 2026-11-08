# Lexicon Personality Bot: notebook agent (v2 judge, seed 1)

Open `lexicon_agent.ipynb` and run all cells. `lexicon_agent_run.ipynb` is the same notebook with outputs from the full P1 + P2 run with style judge v2 (gpt-4o).

Setup: `pip install openai sentence-transformers scikit-learn rapidfuzz pandas numpy`. To make new API calls, copy `.env.example` to `.env` and put your own `OPENAI_API_KEY` in it (`.env` is git-ignored). No key is needed to rerun.
Every API call is cached in `cache/llm_cache.jsonl`, so re-running reproduces the same numbers for $0. The v2 judge run cost $0.82; all runs together cost under $1.00. The seed-1 replies are frozen in `frozen/generations_seed1.csv`, and section 7 loads them instead of regenerating.

## Files
- `data/` P1 and P2 survey answers (teammate names replaced by TM), the scene bank and the 20 labels
- `code/lexicon_retrieval.py` personal RAG store (MiniLM + StyleDistance, CPU, free)
- Retrieval fix (Nov 8, 2026): condition E retrieval is now deterministic (StyleDistance loaded as float32, scores rounded to 6 decimals, ties broken by scene ID); check it with `code/test_retrieval_determinism.py` and `code/validate_retrieval_e.py`. Reported numbers are unchanged because scoring uses the frozen replies.
- `code/lexicon_gen_judge.py` style card, generation prompt, copy check, style and meaning judges, bootstrap CI
- `frozen/` seed-1 test split (2 scenes per label, 40 per person) and the 40 gists per person. Never redraw these.
- `results/` generations, pairwise judgments, meaning scores, style table and guardrails
- `augment/` ChatGPT prompt pack for the confirm/edit/reject round (condition D)

## Notebook sections
1 config, 2 load and merge labels, 3 frozen random split, 4 Structured Outputs tagging and gists, 5 style card,
6 RAG store, 7 generation (A plain, B semantic, C context-aware, D verified, E StyleDistance), 8 judge calibration,
9 evaluation, 10 the agent (understand, retrieve, draft, check up to 3 revisions, learn from feedback), 11 augmentation.

## Rules kept
The "reply properly" rows are excluded (rushed for both people). Test scenes and their twins never enter the store, and a leak assert checks every retrieval.
D runs only after `import_review` adds verified rows.
