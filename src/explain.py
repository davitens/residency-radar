from __future__ import annotations

import hashlib
import json
import os
from typing import Callable

from .enrich import first_json
from .llm import chat
from .models import Program

SYSTEM = (
    "You assess fit between a candidate CV and a research-program posting. "
    'Reply with one JSON object: {"score": 0-100, '
    '"reasons": ["2-4 specific positive fit points"], '
    '"gaps": ["1-3 requirements the CV does not yet show"], '
    '"tailoring": ["1-3 concrete application tips"]}. '
    "Put ONLY positives in reasons; every weakness goes in gaps."
)
CACHE_DIR = "data/llm_cache"


def explain(
    cv_text: str,
    program: Program,
    chat_fn: Callable[..., str] | None = None,
    cache_dir: str = CACHE_DIR,
) -> dict:
    key = hashlib.sha1((cv_text + "||" + program.text).encode("utf-8")).hexdigest()
    path = os.path.join(cache_dir, key + ".json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))

    chat_fn = chat_fn or chat
    data: dict = {"score": None, "reasons": [], "gaps": [], "tailoring": []}
    try:
        user = f"CV:\n{cv_text[:4000]}\n\nPROGRAM ({program.org} - {program.title}):\n{program.text[:4000]}"
        raw = chat_fn(SYSTEM, user)
        parsed = first_json(raw)
        if isinstance(parsed, dict):
            for field in ("score", "reasons", "gaps", "tailoring"):
                if field in parsed:
                    data[field] = parsed[field]
    except Exception as exc:
        data["error"] = str(exc)

    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    return data
