from datetime import date

import numpy as np
import pytest

from src.match import closed_watchlist, manual_watchlist, open_programs, rank
from src.models import Program

TODAY = date(2026, 9, 25)


def fake_embed(texts):
    out = []
    for text in texts:
        t = text.lower()
        if "cvmarker" in t:
            v = np.array([1.0, 0.0, 0.0])
        elif "python llm" in t:
            v = np.array([0.9, 0.1, 0.0])
        elif "unrelated" in t:
            v = np.array([0.0, 1.0, 0.0])
        else:
            v = np.array([0.1, 0.1, 1.0])
        out.append(v / np.linalg.norm(v))
    return np.array(out)


def test_empty_cv_raises():
    with pytest.raises(ValueError):
        rank([Program("O", "T", "https://a", text="x" * 300)], "")


def test_eligibility_gate_and_ordering():
    cv = "cvmarker " * 20
    good = Program("O", "Good Residency", "https://a", text="python llm " + "x" * 300, status="open")
    gated = Program("O", "Gated Fellowship", "https://b", text="must be authorized to work in the us " + "x" * 300, status="open")
    unrelated = Program("O", "Unrelated Residency", "https://c", text="unrelated " + "y" * 300, status="open")
    out = rank(
        [good, gated, unrelated],
        cv,
        today=TODAY,
        embed_fn=fake_embed,
        skills=["python", "llm"],
    )
    titles = [r["title"] for r in out]
    assert "Gated Fellowship" not in titles
    assert titles[0] == "Good Residency"


def test_rank_requires_open_offer_only():
    cv = "cvmarker " * 20
    page = Program("O", "Program Page Residency", "https://p", text="python llm " + "x" * 300, kind="program_page", status="open")
    unverified = Program("O", "Unknown Residency", "https://u", text="python llm " + "x" * 300, status="unknown")
    assert rank([page, unverified], cv, today=TODAY, embed_fn=fake_embed, skills=["python"]) == []


def test_manual_watchlist_only_unknown():
    unknown_page = Program("O", "Unknown Residency", "https://p", text="x" * 300, kind="program_page", status="unknown")
    open_page = Program("O", "Open Program Residency", "https://q", text="x" * 300, kind="program_page", status="open")
    closed = Program("O", "Closed Residency", "https://c", text="x" * 300, status="closed")
    assert [p["title"] for p in manual_watchlist([unknown_page, open_page, closed])] == ["Unknown Residency"]


def test_open_programs_scored():
    cv = "cvmarker " * 20
    open_page = Program("O", "Open Program Residency", "https://q", text="python llm " + "x" * 300, kind="program_page", status="open")
    assert [r["title"] for r in open_programs([open_page], cv, today=TODAY, embed_fn=fake_embed, skills=["python"])] == ["Open Program Residency"]


def test_rank_excludes_closed():
    cv = "cvmarker " * 20
    open_p = Program("O", "Open Residency", "https://a", text="python llm " + "x" * 300, status="open")
    closed_p = Program("O", "Closed Residency", "https://b", text="python llm " + "x" * 300, status="closed")
    out = rank([open_p, closed_p], cv, today=TODAY, embed_fn=fake_embed, skills=["python", "llm"])
    assert [r["title"] for r in out] == ["Open Residency"]


def test_closed_watchlist():
    closed_p = Program("O", "Closed Residency", "https://b", text="x" * 300, status="closed")
    open_p = Program("O", "Open Residency", "https://a", text="x" * 300, status="open")
    assert [p["title"] for p in closed_watchlist([closed_p, open_p])] == ["Closed Residency"]


def test_short_text_excluded():
    cv = "cvmarker " * 20
    tiny = Program("O", "Tiny Residency", "https://a", text="too short", status="open")
    out = rank([tiny], cv, today=TODAY, embed_fn=fake_embed, skills=["python"])
    assert out == []
