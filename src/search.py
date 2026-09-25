from __future__ import annotations

import json
import os
from urllib.parse import urlparse

DEFAULT_QUERIES = [
    '"AI residency" OR "research residency" 2026',
    '"AI safety fellowship" applications',
    '"machine learning" "residency program"',
    '"research fellowship" LLM alignment funded',
]
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
CANDIDATES_PATH = "data/candidates.json"


def discover(queries: list[str] | None = None, *, api_key: str | None = None, client_fn=None) -> list[str]:
    key = api_key or os.environ.get("BRAVE_API_KEY", "")
    if not key:
        print("BRAVE_API_KEY not set; skipping discovery")
        return []
    import httpx

    if client_fn is None:
        def client_fn(url, params, headers):
            return httpx.get(url, params=params, headers=headers, timeout=20)

    out: list[str] = []
    for query in queries or DEFAULT_QUERIES:
        try:
            resp = client_fn(BRAVE_URL, {"q": query, "count": 20},
                             {"Accept": "application/json", "X-Subscription-Token": key})
            resp.raise_for_status()
            for item in resp.json().get("web", {}).get("results", []):
                url = item.get("url", "")
                if url and url not in out:
                    out.append(url)
        except Exception as exc:
            print(f"search failed for {query!r}: {exc}")
    return out


def filter_known(urls: list[str], known_domains: set[str]) -> list[str]:
    fresh = []
    for url in urls:
        domain = urlparse(url).netloc.removeprefix("www.")
        if domain and not any(domain == d or domain.endswith("." + d) for d in known_domains):
            fresh.append(url)
    return fresh


def main() -> None:
    urls = discover()
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as fh:
        json.dump(urls, fh, indent=2)
    print(f"wrote {CANDIDATES_PATH} ({len(urls)} candidate URLs) - review before adding to sources.yaml")


if __name__ == "__main__":
    main()
