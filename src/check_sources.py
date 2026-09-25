from __future__ import annotations

import httpx

from .fetch import ATS_URLS
from .sources import load_settings, load_sources


def check(client=None, settings: dict | None = None) -> list[tuple[str, str, object]]:
    settings = settings or load_settings()
    user_agent = settings["user_agent"]

    def default_client(url: str):
        return httpx.get(url, headers={"User-Agent": user_agent}, timeout=20, follow_redirects=True)

    client = client or default_client
    results: list[tuple[str, str, object]] = []
    for src in load_sources():
        url = src.get("url") or ATS_URLS[src["type"]].format(slug=src["slug"])
        try:
            results.append((src["name"], url, client(url).status_code))
        except Exception as exc:
            results.append((src["name"], url, f"ERR {exc}"))
    return results


def main() -> None:
    for name, url, status in check():
        print(f"{str(status):>6}  {name:34} {url}")


if __name__ == "__main__":
    main()
