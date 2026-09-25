from __future__ import annotations

import json
import logging
import os
from datetime import date

import numpy as np

from .embed import embed_texts
from .filters import is_eligible, is_open, is_residency, parse_deadline
from .lexical import bm25_scores, load_skills, skill_overlap
from .models import Program, load_programs

log = logging.getLogger(__name__)

CV_PATH = "data/cv.txt"
PROGRAMS_PATH = "data/programs.json"
RANKED_PATH = "data/ranked.json"
MIN_TEXT_LEN = 200
WEIGHTS = {"embedding": 0.55, "bm25": 0.25, "skills": 0.15, "recency": 0.05}


def score(embedding: float, bm25: float, skills: float, recency: float, weights: dict = WEIGHTS) -> float:
    total = (
        weights["embedding"] * embedding
        + weights["bm25"] * bm25
        + weights["skills"] * skills
        + weights["recency"] * recency
    )
    return round(float(total), 4)


def _recency(posted: str, today: date) -> float:
    d = parse_deadline(posted, today)
    if not d:
        return 0.0
    days = (today - d).days
    if days < 0:
        return 1.0
    return max(0.0, 1.0 - days / 365.0)


def rank(
    programs: list[Program],
    cv_text: str,
    today: date | None = None,
    weights: dict = WEIGHTS,
    embed_fn=embed_texts,
    skills: list[str] | None = None,
    kinds: tuple[str, ...] = ("offer",),
    statuses: tuple[str, ...] = ("open", "rolling"),
) -> list[dict]:
    if not cv_text or len(cv_text.strip()) < 50:
        raise ValueError("empty CV")
    today = today or date.today()
    skills = load_skills() if skills is None else skills

    # Recommendations are specific, currently-open offers only. Program pages and
    # unknown-status entries go to the other lists instead.
    eligible = [
        p
        for p in programs
        if p.kind in kinds
        and p.status in statuses
        and is_eligible(p, today, cv_text)
        and is_residency(p)
        and len(p.text) >= MIN_TEXT_LEN
    ]
    if not eligible:
        return []

    texts = [p.text for p in eligible]
    cv_vec = embed_fn([cv_text])[0]
    sims = embed_fn(texts) @ cv_vec
    lexical = bm25_scores(cv_text, texts)

    results = []
    for i, p in enumerate(eligible):
        sk = skill_overlap(cv_text, p.text, skills)
        rec = _recency(p.posted, today)
        row = p.to_dict()
        row.update(
            score=score(float(sims[i]), float(lexical[i]), sk, rec, weights),
            embedding_sim=round(float(sims[i]), 4),
            bm25=round(float(lexical[i]), 4),
            skill_overlap=round(sk, 4),
        )
        results.append(row)
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def _enrich(ranked: list[dict], cv_text: str, top_k: int = 20) -> None:
    from .explain import explain
    from .models import Program

    for row in ranked[:top_k]:
        program = Program.from_dict(row)
        extra = explain(cv_text, program)
        row["reasons"] = extra.get("reasons") or []
        row["gaps"] = extra.get("gaps") or []
        row["llm_score"] = extra.get("score")


def closed_watchlist(programs: list[Program]) -> list[dict]:
    return [
        p.to_dict()
        for p in programs
        if is_residency(p) and p.status == "closed" and len(p.text) >= MIN_TEXT_LEN
    ]


def open_programs(programs: list[Program], cv_text: str, **kwargs) -> list[dict]:
    """Flexible programs with no specific posting, but explicitly open/rolling."""
    return rank(programs, cv_text, kinds=("program_page",), statuses=("open", "rolling"), **kwargs)


def manual_watchlist(programs: list[Program]) -> list[dict]:
    """Entries whose open/closed status could not be determined."""
    return [
        p.to_dict()
        for p in programs
        if is_residency(p) and p.status == "unknown" and len(p.text) >= MIN_TEXT_LEN
    ]


def _sibling(out_path: str, suffix: str) -> str:
    if not out_path.endswith(".json"):
        return out_path + suffix + ".json"
    return out_path[:-5] + suffix + ".json"


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Rank programs against a CV.")
    parser.add_argument("--cv", default=CV_PATH)
    parser.add_argument("--programs", default=PROGRAMS_PATH)
    parser.add_argument("--out", default=RANKED_PATH)
    parser.add_argument("--closed", default=None, help="where to write the closed/watchlist JSON")
    parser.add_argument("--manual", default=None, help="where to write the manual programs JSON")
    parser.add_argument("--open-programs", default=None, help="where to write open program pages JSON")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cv_text = open(args.cv, encoding="utf-8").read()
    programs = load_programs(args.programs)
    use_llm = os.environ.get("ENABLE_LLM", "").lower() in {"1", "true", "yes"}

    ranked = rank(programs, cv_text)
    if use_llm and ranked:
        log.info("enriching top %d offers with LLM", min(20, len(ranked)))
        _enrich(ranked, cv_text)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(ranked, fh, indent=2, ensure_ascii=False)

    programs_open = open_programs(programs, cv_text)
    if use_llm and programs_open:
        log.info("enriching top %d open programs with LLM", min(20, len(programs_open)))
        _enrich(programs_open, cv_text)
    open_programs_path = args.open_programs or _sibling(args.out, "_programs")
    with open(open_programs_path, "w", encoding="utf-8") as fh:
        json.dump(programs_open, fh, indent=2, ensure_ascii=False)

    closed = closed_watchlist(programs)
    closed_path = args.closed or _sibling(args.out, "_closed")
    with open(closed_path, "w", encoding="utf-8") as fh:
        json.dump(closed, fh, indent=2, ensure_ascii=False)

    manual = manual_watchlist(programs)
    manual_path = args.manual or _sibling(args.out, "_manual")
    with open(manual_path, "w", encoding="utf-8") as fh:
        json.dump(manual, fh, indent=2, ensure_ascii=False)

    print(
        f"wrote {args.out} ({len(ranked)} open offers) + "
        f"{open_programs_path} ({len(programs_open)} open programs) + "
        f"{closed_path} ({len(closed)} closed) + {manual_path} ({len(manual)} manual)"
    )


if __name__ == "__main__":
    main()
