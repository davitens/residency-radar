from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.robotparser as robotparser
from urllib.parse import urlparse

from .extract import (
    MIN_TEXT_LEN,
    discover_offer_links,
    extract_text,
    page_title,
    parse_ashby,
    parse_greenhouse,
    parse_lever,
)
from .models import Program, save_programs
from .sources import load_settings, load_sources
from .status import detect_status, finalize_status

log = logging.getLogger(__name__)

PROGRAMS_PATH = "data/programs.json"
ATS_URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}
PARSERS = {"greenhouse": parse_greenhouse, "lever": parse_lever, "ashby": parse_ashby}

_last_request = 0.0
_robots_cache: dict[str, robotparser.RobotFileParser | None] = {}


def _default_client(url: str, user_agent: str) -> str:
    import httpx

    resp = httpx.get(url, headers={"User-Agent": user_agent}, timeout=20, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _cache_path(url: str, cache_dir: str) -> str:
    return os.path.join(cache_dir, hashlib.sha1(url.encode("utf-8")).hexdigest() + ".txt")


def _robots_for(url: str, user_agent: str, client_fn) -> robotparser.RobotFileParser | None:
    root = "{0.scheme}://{0.netloc}".format(urlparse(url))
    if root in _robots_cache:
        return _robots_cache[root]
    parser: robotparser.RobotFileParser | None = None
    try:
        parser = robotparser.RobotFileParser()
        parser.parse(client_fn(root + "/robots.txt", user_agent).splitlines())
    except Exception:
        parser = None  # unreachable robots.txt -> stay permissive
    _robots_cache[root] = parser
    return parser


def is_allowed(url: str, user_agent: str = "residence-finder", client_fn=None) -> bool:
    client_fn = client_fn or _default_client
    parser = _robots_for(url, user_agent, client_fn)
    if parser is None:
        return True
    try:
        return parser.can_fetch(user_agent, url)
    except Exception:
        return True


def fetch_url(
    url: str,
    *,
    cache_dir: str = "data/cache",
    rate_limit_s: float = 2.0,
    ttl_s: float = 86400,
    user_agent: str = "residence-finder/0.1 (personal research)",
    client_fn=None,
) -> str:
    global _last_request
    client_fn = client_fn or _default_client
    path = _cache_path(url, cache_dir)
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < ttl_s:
        return open(path, encoding="utf-8").read()
    if not is_allowed(url, user_agent, client_fn):
        log.warning("robots.txt disallows %s", url)
        return ""
    if rate_limit_s:
        wait = rate_limit_s - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
    try:
        text = client_fn(url, user_agent)
    except Exception as exc:
        log.warning("fetch failed for %s: %s", url, exc)
        return ""
    _last_request = time.time()
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def dedupe(programs: list[Program]) -> list[Program]:
    seen_urls: set[str] = set()
    seen_names: set[tuple[str, str]] = set()
    out: list[Program] = []
    for p in programs:
        name = (p.org.strip().lower(), p.title.strip().lower())
        if p.url in seen_urls or name in seen_names:
            continue
        seen_urls.add(p.url)
        seen_names.add(name)
        out.append(p)
    return out


def ingest(sources: list[dict], settings: dict, *, client_fn=None, cache_dir: str = "data/cache") -> list[Program]:
    common = dict(
        cache_dir=cache_dir,
        rate_limit_s=settings["rate_limit_s"],
        ttl_s=settings["cache_ttl_s"],
        user_agent=settings["user_agent"],
        client_fn=client_fn,
    )
    programs: list[Program] = []
    for src in sources:
        name, kind = src["name"], src["type"]
        try:
            url = src.get("url") or ATS_URLS[kind].format(slug=src["slug"])
            raw = fetch_url(url, **common)
            if not raw:
                continue
            if kind == "page":
                programs.extend(_page_programs(src, url, raw, common))
            else:
                parsed = PARSERS[kind](json.loads(raw), org=name)
                for program in parsed:
                    program.source = kind
                    program.parent = name
                    program.kind = "offer"
                    program.status, program.status_evidence = "open", "active job posting"
                programs.extend(parsed)
        except Exception as exc:
            log.warning("source %r failed: %s", name, exc)
    return dedupe(programs)


_GENERIC_TITLE = {"program", "programs", "apply", "home", "fellowship", "residency", "about", "overview"}


def offer_title(page_title: str, parent: str) -> str:
    title = (page_title or "").strip()
    if not title or len(title) > 70 or title.lower() in _GENERIC_TITLE:
        return parent
    return title


def _page_programs(src: dict, url: str, raw: str, common: dict) -> list[Program]:
    """Turn a program page into specific offers (linked apply/ATS pages), or the page itself if none."""
    org = src.get("org", src["name"])
    parent = src.get("title", src["name"])
    # An explicit offer_links list (even empty) overrides auto-discovery.
    links = src["offer_links"] if "offer_links" in src else discover_offer_links(raw, url)
    programs: list[Program] = []
    for link in links:
        sub = fetch_url(link, **common)
        if not sub:
            continue
        text = extract_text(sub)
        if len(text) < MIN_TEXT_LEN:
            continue
        status, evidence = detect_status(text)
        programs.append(
            Program(
                org=org,
                title=offer_title(page_title(sub, parent), parent),
                url=link,
                text=text,
                source="curated",
                parent=parent,
                kind="offer",
                status=status,
                status_evidence=evidence,
            )
        )
    if programs:
        return programs
    text = extract_text(raw)
    status, evidence = detect_status(text)
    return [
        Program(
            org=org,
            title=parent,
            url=url,
            text=text,
            source="curated",
            parent=parent,
            kind="program_page",
            status=status,
            status_evidence=evidence,
        )
    ]


def enrich_candidates(
    programs: list[Program],
    *,
    chat_fn=None,
    cache_dir: str = "data/enrich_cache",
    limit: int | None = None,
) -> list[Program]:
    from .enrich import enrich_program
    from .filters import is_residency

    candidates = [p for p in programs if is_residency(p) and len(p.text) >= MIN_TEXT_LEN]
    if limit:
        candidates = candidates[:limit]
    for program in candidates:
        enrich_program(program, chat_fn=chat_fn, cache_dir=cache_dir)
        finalize_status(program)
    return candidates


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    programs = ingest(load_sources(), settings)

    if os.environ.get("ENABLE_ENRICH", "1") != "0":
        from .llm import available

        if available():
            enriched = enrich_candidates(programs)
            print(f"enriched {len(enriched)} residency candidates")
        else:
            log.warning("LLM daemon unavailable; skipping enrichment (set ENABLE_ENRICH=0 to silence)")

    save_programs(programs, PROGRAMS_PATH)
    print(f"wrote {PROGRAMS_PATH} ({len(programs)} programs)")


if __name__ == "__main__":
    main()
