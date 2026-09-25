from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import trafilatura
from bs4 import BeautifulSoup

from .models import Program

log = logging.getLogger(__name__)

MIN_TEXT_LEN = 200

# ATS job links are NOT scraped from pages: those come from explicit ATS feeds, so a careers
# page cannot leak unrelated engineering jobs into the residency list.
_OFFER_PATH = re.compile(
    r"/(apply|residenc(?:y|ies)|fellowships?|scholars?|residents?)\b|/programs?/[a-z0-9-]+", re.I
)
_HREF = re.compile(r"""href=["']([^"']+)["']""", re.I)


def _host(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.")


def discover_offer_links(html: str, base_url: str, cap: int = 6) -> list[str]:
    """Specific offer/apply pages linked from a program page (ATS job URLs or same-domain offer paths)."""
    base_host = _host(base_url)
    found: list[str] = []
    for href in _HREF.findall(html or ""):
        if href.startswith(("#", "mailto:", "javascript:")):
            continue
        full = urljoin(base_url, href).split("#")[0].rstrip("/")
        if not full.startswith("http"):
            continue
        parsed = urlparse(full)
        if _host(full) == base_host and _OFFER_PATH.search(parsed.path):
            found.append(full)
    unique: list[str] = []
    for url in found:
        if url not in unique:
            unique.append(url)
    return unique[:cap]


def page_title(html: str, fallback: str = "") -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in ("h1", "title"):
        el = soup.find(tag)
        if el and el.get_text(strip=True):
            text = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
            return text.split("|")[0].split(" - ")[0].strip()[:120]
    return fallback


def extract_text(html: str) -> str:
    if not html:
        return ""
    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    if not text.strip():
        try:
            text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        except Exception:  # pragma: no cover - defensive
            text = ""
    return text.strip()


def _clean(html: str) -> str:
    return extract_text(html) if ("<" in html and ">" in html) else (html or "").strip()


def parse_greenhouse(data: dict, org: str = "Greenhouse") -> list[Program]:
    out: list[Program] = []
    for job in (data or {}).get("jobs", []) or []:
        try:
            out.append(
                Program(
                    org=(job.get("company_name") or org),
                    title=job.get("title", ""),
                    url=job.get("absolute_url", ""),
                    text=_clean(job.get("content", "")),
                    location=(job.get("location") or {}).get("name", ""),
                    posted=(job.get("updated_at") or job.get("created_at") or "")[:10],
                    source="greenhouse",
                )
            )
        except Exception as exc:  # pragma: no cover - schema drift guard
            log.warning("greenhouse item skipped: %s", exc)
    return out


def parse_lever(data: list, org: str = "Lever") -> list[Program]:
    out: list[Program] = []
    for job in data or []:
        try:
            cats = job.get("categories") or {}
            out.append(
                Program(
                    org=(job.get("company") or org),
                    title=job.get("text", ""),
                    url=job.get("hostedUrl", ""),
                    text=_clean(job.get("descriptionPlain") or job.get("description") or ""),
                    location=cats.get("location", ""),
                    posted=str(job.get("createdAt", ""))[:10],
                    source="lever",
                )
            )
        except Exception as exc:  # pragma: no cover
            log.warning("lever item skipped: %s", exc)
    return out


def parse_ashby(data: dict, org: str = "Ashby") -> list[Program]:
    out: list[Program] = []
    for job in (data or {}).get("jobs", []) or []:
        try:
            out.append(
                Program(
                    org=org,
                    title=job.get("title", ""),
                    url=job.get("jobUrl") or job.get("applyUrl", ""),
                    text=_clean(job.get("descriptionPlain") or job.get("descriptionHtml") or ""),
                    location=job.get("location", ""),
                    posted=str(job.get("publishedAt") or job.get("updatedAt") or "")[:10],
                    eligibility="remote" if job.get("isRemote") else "",
                    source="ashby",
                )
            )
        except Exception as exc:  # pragma: no cover
            log.warning("ashby item skipped: %s", exc)
    return out
