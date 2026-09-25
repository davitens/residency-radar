from __future__ import annotations

import yaml

VALID_TYPES = {"page", "greenhouse", "lever", "ashby"}
DEFAULT_PATH = "data/sources.yaml"


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_sources(path: str = DEFAULT_PATH) -> list[dict]:
    data = _load(path)
    sources = data.get("sources", [])
    for src in sources:
        if src.get("type") not in VALID_TYPES:
            raise ValueError(f"unknown source type: {src.get('type')!r} in {src.get('name')!r}")
        if not src.get("url") and not src.get("slug"):
            raise ValueError(f"source {src.get('name')!r} needs a url or slug")
    return sources


def load_reference_links(path: str = DEFAULT_PATH) -> list[dict]:
    return _load(path).get("reference_links", []) or []


def load_settings(path: str = DEFAULT_PATH) -> dict:
    settings = _load(path).get("settings", {})
    return {
        "rate_limit_s": settings.get("rate_limit_s", 2.0),
        "user_agent": settings.get("user_agent", "residence-finder/0.1 (personal research)"),
        "cache_ttl_s": settings.get("cache_ttl_s", 86400),
    }
