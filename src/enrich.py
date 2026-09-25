from __future__ import annotations

import hashlib
import json
import os
from typing import Callable

from .llm import chat
from .models import Program

FIELDS = ["deadline", "location", "eligibility", "stipend", "status", "status_evidence"]
CACHE_DIR = "data/enrich_cache"
SYSTEM = "You extract structured data from research-program postings. Reply with one JSON object only."

USER_TEMPLATE = """Extract these fields from the posting. Use "" when unknown.
- deadline: application deadline as YYYY-MM-DD, or "" if rolling/unknown
- location: city/country, or "Remote"
- eligibility: one short phrase (e.g. "PhD required", "open to career changers")
- stipend: "yes" / "no" / an amount, or ""
- status: are applications currently being accepted? one of: open, closed, rolling, unknown
- status_evidence: a short quote from the posting that supports the status

Posting:
{text}"""


def first_json(text: str) -> dict:
    """Extract the first balanced JSON object from an LLM reply that may wrap it in prose."""
    start = text.find("{")
    if start == -1:
        return {}
    depth, in_str, escape = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


def _cache_path(text: str, cache_dir: str) -> str:
    return os.path.join(cache_dir, hashlib.sha1(text.encode("utf-8")).hexdigest() + ".json")


def extract_fields(text: str, chat_fn: Callable[..., str] | None = None, cache_dir: str | None = None) -> dict:
    if not (text or "").strip():
        return {}
    path = _cache_path(text, cache_dir) if cache_dir else None
    if path and os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))

    chat_fn = chat_fn or chat
    try:
        data = first_json(chat_fn(SYSTEM, USER_TEMPLATE.format(text=text[:6000])))
    except Exception:
        return {}
    if not isinstance(data, dict) or not data:
        return {}
    fields = {k: data.get(k, "") for k in FIELDS}

    if path:
        os.makedirs(cache_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(fields, fh, ensure_ascii=False)
    return fields


ALLOWED_STATUS = {"open", "closed", "rolling", "unknown"}


def enrich_program(
    program: Program, chat_fn: Callable[..., str] | None = None, cache_dir: str = CACHE_DIR
) -> Program:
    """Fill deadline/location/eligibility/stipend from the posting text; leave existing values on failure."""
    fields = dict(extract_fields(program.text, chat_fn=chat_fn, cache_dir=cache_dir))
    status = str(fields.pop("status", "") or "").strip().lower()
    if status in ALLOWED_STATUS and status != "unknown":
        program.status = status
    for key, value in fields.items():
        if value:
            setattr(program, key, str(value)[:200])
    return program


if __name__ == "__main__":  # tiny self-check, no network
    assert first_json('blah {"a": 1, "b": {"c": 2}} trailing') == {"a": 1, "b": {"c": 2}}
    assert first_json("no json here") == {}
    assert first_json('{"s": "a } b"}') == {"s": "a } b"}
    print("enrich self-check OK")
