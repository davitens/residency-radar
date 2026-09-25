from __future__ import annotations

import re

import numpy as np
from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9+#.]+")
DEFAULT_SKILLS = "data/skills.txt"


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def bm25_scores(cv_text: str, docs: list[str]) -> np.ndarray:
    docs = list(docs)
    if not docs:
        return np.zeros(0)
    corpus = [tokenize(d) for d in docs]
    if not any(corpus):
        return np.zeros(len(docs))
    scores = np.asarray(BM25Okapi(corpus).get_scores(tokenize(cv_text)), dtype=float)
    lo, hi = float(scores.min()), float(scores.max())
    if hi - lo < 1e-9:
        return np.zeros(len(docs))
    return (scores - lo) / (hi - lo)


def load_skills(path: str = DEFAULT_SKILLS) -> list[str]:
    seen: dict[str, None] = {}
    for line in open(path, encoding="utf-8"):
        s = line.strip().lower()
        if s:
            seen.setdefault(s, None)
    return list(seen)


def _hits(text: str, skills: list[str]) -> set[str]:
    blob = (text or "").lower()
    return {s for s in skills if s in blob}


def skill_overlap(cv_text: str, doc: str, skills: list[str], idf: dict | None = None) -> float:
    cv_skills = _hits(cv_text, skills)
    if not cv_skills:
        return 0.0
    matched = cv_skills & _hits(doc, skills)
    if idf:
        denom = sum(idf.get(s, 1.0) for s in cv_skills)
        num = sum(idf.get(s, 1.0) for s in matched)
    else:
        denom, num = len(cv_skills), len(matched)
    return num / denom if denom else 0.0
