"""Lexicon retrieval: personal example store + retrievers for conditions B, C, D, E.

Free, local, CPU only. No API key needed.
  semantic model : sentence-transformers/all-MiniLM-L6-v2   (what the message is about)
  style model    : StyleDistance/styledistance              (how the reply sounds)

Usage
    from lexicon_retrieval import ExampleStore
    store = ExampleStore.from_survey("p1_survey.csv", "prompt_bank_v2.csv",
                                     exclude_scene_ids=frozen_test_ids)   # test split never enters the store
    refs = store.retrieve("B_semantic", user_id="P1", incoming="...", k=3)
    # refs are lexicon_gen_judge.Ref objects -> pass straight to generate_reply(refs=refs)

Rules baked in
  * one row per answered reply; abstains, empty replies and pilot rows are dropped
  * default pool is the chat register only (survey-register repeats are excluded; ProjLexicon
    found they measure fatigue, not a formal register)
  * every scene_id in exclude_scene_ids is removed in both registers, so a test scene's twin cannot leak
  * every query is filtered by user_id: P1 never gets P2's examples
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    from lexicon_gen_judge import Ref
except ImportError:  # standalone use
    @dataclass
    class Ref:
        incoming: str
        reply: str
        label: str = ""
        sender_role: str = ""
        stakes: str = ""

SEMANTIC_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
STYLE_MODEL = "StyleDistance/styledistance"
_MODELS: dict = {}
# E quantizes cosine scores to six decimals, then orders by persistent row identity.
# Rounding reduces floating-point jitter; frozen generations remain the evaluation source
# of truth. It cannot guarantee identical retrieval across different model revisions.
E_SCORE_DECIMALS = 6


def _model(name):
    if name not in _MODELS:
        from sentence_transformers import SentenceTransformer
        kwargs = {}
        if name == STYLE_MODEL:
            import torch
            # Its saved dtype may be bfloat16; CPU reduction differences at that
            # precision are too large to repair with cosine-score rounding alone.
            kwargs["model_kwargs"] = {"dtype": torch.float32}
        _MODELS[name] = SentenceTransformer(name, device="cpu", **kwargs)
    return _MODELS[name]


def embed(texts, which="semantic") -> np.ndarray:
    name = SEMANTIC_MODEL if which == "semantic" else STYLE_MODEL
    return _model(name).encode(list(texts), normalize_embeddings=True,
                               batch_size=32, show_progress_bar=False)


def strip_sender(msg: str) -> str:
    """'Phil: can you take the slides' -> 'can you take the slides' (names never reach the embedder)."""
    return re.sub(r"^[^:]{1,30}:\s*", "", str(msg)).strip()


ORIGINS_DEFAULT = ("survey", "real_chat", "chatbot_rewrite", "gpt_confirmed", "gpt_edited")


class ExampleStore:
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True)
        self.sem = embed(self.df["query_text"], "semantic") if len(df) else np.zeros((0, 384))
        self.sty = embed(self.df["response"], "style") if len(df) else np.zeros((0, 768))

    # ---------- building ----------
    @classmethod
    def from_survey(cls, survey_csv, bank_csv, exclude_scene_ids=(), registers=("chat",),
                    extra_rows: pd.DataFrame | None = None):
        paths = [survey_csv] if isinstance(survey_csv, (str, bytes)) or hasattr(survey_csv, "__fspath__") else list(survey_csv)
        s = pd.concat([pd.read_csv(x) for x in paths], ignore_index=True)   # P1 + P2 in one store
        b = pd.read_csv(bank_csv)
        s = s[s["round"].astype(str) != "pilot"]
        s = s[s["item_type"] == "scene"]
        resp = s["response"].fillna("").astype(str).str.strip()
        s = s[(~s["abstain"].astype(str).str.lower().eq("true")) & (resp != "")]
        s = s[s["register"].isin(registers)]
        ex = exclude_scene_ids
        if isinstance(ex, dict):            # per-person test ids: {"P1": {...}, "P2": {...}}
            s = s[[sid not in ex.get(u, ()) for u, sid in zip(s["user_id"], s["scene_id"])]]
        else:
            s = s[~s["scene_id"].isin(set(ex))]
        meta = b[["scene_id", "target_label", "sender_role", "stakes", "context"]]
        s = s.drop(columns=[c for c in ("target_label",) if c in s]).merge(meta, on="scene_id", how="left")
        s["incoming"] = s["shown_message"].map(strip_sender)
        s["origin"] = s.get("origin", "survey").fillna("survey")
        rows = s[["user_id", "scene_id", "register", "incoming", "response", "target_label",
                  "sender_role", "stakes", "context", "origin"]].copy()
        if extra_rows is not None:          # condition D: gpt_confirmed / gpt_edited rows
            rows = pd.concat([rows, extra_rows[rows.columns]], ignore_index=True)
        rows["query_text"] = rows["incoming"]
        rows["response"] = rows["response"].astype(str).str.strip()
        return cls(rows)

    def save(self, path):
        np.savez(path, sem=self.sem, sty=self.sty)
        self.df.to_csv(str(path).replace(".npz", ".csv"), index=False)

    # ---------- retrieval ----------
    def _mask(self, user_id, origins, label=None, sender_role=None):
        m = (self.df["user_id"] == user_id) & self.df["origin"].isin(origins)
        if label:
            m &= self.df["target_label"] == label
        if sender_role:
            m &= self.df["sender_role"] == sender_role
        return m.to_numpy()

    def _refs(self, idx):
        return [Ref(incoming=r.incoming, reply=r.response, label=str(r.target_label or ""),
                    sender_role=str(r.sender_role or ""), stakes=str(r.stakes or ""))
                for r in self.df.iloc[idx].itertuples()]

    def _stable_rank(self, ids, scores, k):
        """Descending quantized score, then scene ID (never current DataFrame position)."""
        def identity(i):
            row = self.df.iloc[i]
            return tuple(str(row.get(col, "")) for col in
                         ("user_id", "scene_id", "register", "origin", "incoming", "response"))
        rounded = np.round(np.asarray(scores, dtype=np.float64), E_SCORE_DECIMALS)
        order = sorted(range(len(ids)), key=lambda j: (-rounded[j], identity(ids[j])))
        return [int(ids[j]) for j in order[:k]]

    def _topk(self, qvec, mask, k, stable=False):
        ids = np.flatnonzero(mask)
        if not len(ids):
            return []
        if stable:
            scores = self.sem[ids].astype(np.float64) @ np.asarray(qvec, dtype=np.float64)
            return self._stable_rank(ids, scores, k)
        scores = self.sem[ids] @ qvec
        return list(ids[np.argsort(-scores)[:k]])

    def style_centroid(self, user_id, origins=ORIGINS_DEFAULT):
        ids = np.flatnonzero(self._mask(user_id, origins))
        c = self.sty[ids].mean(0)
        return c / (np.linalg.norm(c) + 1e-9)

    def retrieve(self, condition, user_id, incoming, k=3, context="", intended_meaning="",
                 label=None, sender_role=None, include_gpt=False, return_rows=False):
        """condition: A_plain | B_semantic | C_context | D_verified | E_styledistance"""
        origins = ORIGINS_DEFAULT if (include_gpt or condition.startswith("D")) else ("survey", "real_chat", "chatbot_rewrite")
        if condition.startswith("A") or k == 0:
            return []
        incoming = strip_sender(incoming)
        if condition.startswith("B"):
            q = embed([incoming])[0]
            idx = self._topk(q, self._mask(user_id, origins), k)
        elif condition.startswith(("C", "D")):
            # context-aware: query includes context + intended meaning, metadata filter on label/role,
            # relaxing the filter step by step if too few matches
            q = embed([" ".join(x for x in (context, incoming, intended_meaning) if x)])[0]
            idx = []
            for lab, role in ((label, sender_role), (label, None), (None, None)):
                for i in self._topk(q, self._mask(user_id, origins, lab, role), k):
                    if i not in idx:
                        idx.append(i)
                if len(idx) >= k:
                    break
            idx = idx[:k]
        elif condition.startswith("E"):
            # style-aware: 15 topical candidates, re-ranked by closeness to the person's style centroid
            q = embed([incoming])[0]
            cand = self._topk(q, self._mask(user_id, origins), 15, stable=True)
            if not cand:
                return []
            # Canonical reduction order + float64 accumulation avoid row-order drift.
            pool = np.flatnonzero(self._mask(user_id, origins))
            pool = self._stable_rank(pool, np.zeros(len(pool)), len(pool))
            c = self.sty[pool].astype(np.float64).mean(0)
            c /= np.linalg.norm(c) + 1e-9
            sty = self.sty[cand].astype(np.float64) @ c
            idx = self._stable_rank(cand, sty, k)
        else:
            raise ValueError(condition)
        return self.df.iloc[idx] if return_rows else self._refs(idx)

    # ---------- metric helper (supporting only; circular for E) ----------
    def style_similarity(self, user_id, texts):
        c = self.style_centroid(user_id)
        return (embed(texts, "style") @ c).tolist()
