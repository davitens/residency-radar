from __future__ import annotations

import re
from datetime import date

from .filters import parse_deadline
from .models import Program

# Checked before open patterns: a page saying "are now closed. Applications open in January" is closed.
_CLOSED = [
    re.compile(r"applications?[^.\n]{0,60}\bclosed\b", re.I),
    re.compile(r"no longer (?:accepting|taking)", re.I),
    re.compile(r"not (?:currently |now )?accepting", re.I),
    re.compile(r"deadline has passed", re.I),
    re.compile(r"closed for (?:this|the) (?:cohort|cycle|round|year)", re.I),
    re.compile(r"applications? (?:are|is) (?:now )?shut", re.I),
]
_OPEN = [
    re.compile(r"applications?[^.\n]{0,40}\b(?:open|being accepted|accepted)\b", re.I),
    re.compile(r"now accepting", re.I),
    re.compile(r"accepting applications", re.I),
    re.compile(r"apply by", re.I),
    re.compile(r"open until filled", re.I),
    re.compile(r"\brolling (?:applications|basis|admissions|review)", re.I),
]
_ROLLING = re.compile(r"rolling|open until filled|ongoing", re.I)


def _evidence(text: str, pos: int, width: int = 160) -> str:
    start = text.rfind(".", 0, pos) + 1
    end = text.find(".", pos)
    end = len(text) if end == -1 else end + 1
    return re.sub(r"\s+", " ", text[start:end]).strip()[:width]


def detect_status(text: str, deadline: str = "", today: date | None = None) -> tuple[str, str]:
    """Rule-first open/closed detection. Returns (status, evidence)."""
    today = today or date.today()
    blob = text or ""

    for pattern in _CLOSED:
        match = pattern.search(blob)
        if match:
            return "closed", _evidence(blob, match.start())

    parsed = parse_deadline(deadline, today)
    if parsed and parsed < today:
        return "closed", f"deadline {deadline} has passed"
    if parsed:
        return "open", f"deadline {deadline}"

    for pattern in _OPEN:
        match = pattern.search(blob)
        if match:
            status = "rolling" if _ROLLING.search(match.group(0)) else "open"
            return status, _evidence(blob, match.start())

    return "unknown", ""


def finalize_status(program: Program) -> None:
    """Rules win over any LLM guess; keep an LLM 'closed' only when rules are unsure."""
    status, evidence = detect_status(program.text, program.deadline)
    if status != "unknown":
        program.status, program.status_evidence = status, evidence
    elif not program.status or program.status == "unknown":
        program.status, program.status_evidence = "unknown", ""
