from __future__ import annotations

import re
from datetime import date, datetime

from .models import Program

_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d %b, %Y",
    "%B %d %Y",
    "%b %Y",
    "%B %Y",
]
_NO_DEADLINE = {"", "rolling", "ongoing", "open until filled", "n/a", "none", "until filled"}

_US_ONLY = [
    "must be authorized to work in the us",
    "us citizen",
    "u.s. citizen",
    "must reside in the us",
    "work authorization in the united states",
    "authorized to work in the united states",
]
_PHD_REQUIRED = ["phd required", "ph.d. required", "phd is required", "must hold a phd", "must have a phd"]


def parse_deadline(s: str, today: date | None = None) -> date | None:
    if not s:
        return None
    text = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s.strip()).lower()
    if text in _NO_DEADLINE:
        return None
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


RESIDENCY_RE = re.compile(
    r"residen|fellow|scholar|apprentice|trainee|early[- ]career|research intern", re.IGNORECASE
)


NON_RESIDENCY_ROLE = re.compile(
    r"specialist|recruiter|engineer|designer|manager|director|coordinator|analyst|"
    r"accountant|counsel|marketing|sales|\blead\b|\bhead\b",
    re.IGNORECASE,
)


def is_residency(program: Program) -> bool:
    if program.source == "curated":
        return True
    title = program.title or ""
    if not RESIDENCY_RE.search(title):
        return False
    # "Early Careers & Interns Specialist" is HR, not a residency.
    if NON_RESIDENCY_ROLE.search(title) and not re.search(r"residen|fellow|scholar", title, re.IGNORECASE):
        return False
    return True


def is_open(program: Program) -> bool:
    return program.status != "closed"


def is_eligible(program: Program, today: date, cv_text: str = "") -> bool:
    deadline = parse_deadline(program.deadline, today)
    if deadline and deadline < today:
        return False
    blob = f"{program.text} {program.eligibility}".lower()
    cv = (cv_text or "").lower()
    if any(k in blob for k in _US_ONLY) and not any(
        x in cv for x in ["united states", "u.s.", "us citizen", "authorized to work in the us", "green card"]
    ):
        return False
    if any(k in blob for k in _PHD_REQUIRED) and "phd" not in cv and "ph.d" not in cv:
        return False
    return True
