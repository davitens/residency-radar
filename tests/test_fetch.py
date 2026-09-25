from src import fetch
from src.models import Program


def test_fetch_error_returns_empty(tmp_path):
    def boom(url, ua):
        raise RuntimeError("network down")

    assert fetch.fetch_url("https://bad.test/a", cache_dir=str(tmp_path), rate_limit_s=0, client_fn=boom) == ""


def test_cache_hit_does_not_refetch(tmp_path):
    calls = []

    def client(url, ua):
        calls.append(url)
        return "" if "robots" in url else "cached body"

    first = fetch.fetch_url("https://good.test/a", cache_dir=str(tmp_path), rate_limit_s=0, client_fn=client)
    n_after_first = len(calls)
    second = fetch.fetch_url("https://good.test/a", cache_dir=str(tmp_path), rate_limit_s=0, client_fn=client)
    assert first == second == "cached body"
    assert len(calls) == n_after_first


def test_page_source_uses_custom_org_title(tmp_path):
    def client(url, ua):
        if "robots" in url:
            return ""
        return "<html><body><p>" + "residency fellowship details " * 30 + "</p></body></html>"

    sources = [
        {"name": "MATS", "type": "page", "url": "https://mats.test/", "org": "MATS Org", "title": "MATS Program"}
    ]
    settings = {"rate_limit_s": 0, "cache_ttl_s": 86400, "user_agent": "test"}
    programs = fetch.ingest(sources, settings, client_fn=client, cache_dir=str(tmp_path / "cache"))
    assert len(programs) == 1
    assert programs[0].org == "MATS Org"
    assert programs[0].title == "MATS Program"


def test_offer_title():
    assert fetch.offer_title("MATS Winter 2027", "ML Alignment Theory Scholars (MATS)") == "MATS Winter 2027"
    assert fetch.offer_title("Program", "Schmidt Science Fellows") == "Schmidt Science Fellows"
    assert fetch.offer_title("", "CHAI") == "CHAI"
    assert fetch.offer_title("A very long sentence " * 5, "FAR AI") == "FAR AI"


def test_enrich_candidates_filters_and_caches(tmp_path):
    calls = {"n": 0}

    def chat_fn(system, user):
        calls["n"] += 1
        return '{"deadline":"2026-06-01","location":"Remote","eligibility":"","stipend":""}'

    residency = Program("OpenAI", "AI Residency 2026", "https://a", text="x" * 300, source="ashby")
    non_residency = Program("OpenAI", "Senior Engineer", "https://b", text="x" * 300, source="ashby")
    short = Program("MATS", "Fellowship", "https://c", text="short", source="curated")

    candidates = fetch.enrich_candidates(
        [residency, non_residency, short], chat_fn=chat_fn, cache_dir=str(tmp_path)
    )
    assert candidates == [residency]
    assert residency.deadline == "2026-06-01"
    assert non_residency.deadline == "" and short.deadline == ""
    assert calls["n"] == 1


def test_ingest_survives_one_bad_source(tmp_path):
    def client(url, ua):
        if "bad.test" in url:
            raise RuntimeError("boom")
        if "robots" in url:
            return ""
        if url.endswith(".json"):
            return '{"jobs": []}'
        return "<html><body><p>" + "research fellowship program details " * 20 + "</p></body></html>"

    sources = [
        {"name": "Bad", "type": "page", "url": "https://bad.test/"},
        {"name": "Good", "type": "page", "url": "https://good.test/"},
        {"name": "GH", "type": "greenhouse", "slug": "acme"},
    ]
    settings = {"rate_limit_s": 0, "cache_ttl_s": 86400, "user_agent": "test"}
    programs = fetch.ingest(sources, settings, client_fn=client, cache_dir=str(tmp_path / "cache"))
    assert any(p.org == "Good" for p in programs)
