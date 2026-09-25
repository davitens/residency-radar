from src.extract import discover_offer_links, extract_text, parse_greenhouse, parse_lever


def test_empty_extraction():
    assert extract_text("") == ""
    assert extract_text("<html><body></body></html>") == ""


def test_malformed_greenhouse_returns_empty():
    assert parse_greenhouse({}) == []
    assert parse_greenhouse({"jobs": "not-a-list"}) == []
    assert parse_greenhouse(None) == []


def test_valid_greenhouse():
    data = {
        "jobs": [
            {
                "title": "AI Resident",
                "absolute_url": "https://gh/1",
                "location": {"name": "Remote"},
                "content": "<p>" + "machine learning research " * 20 + "</p>",
                "updated_at": "2026-09-01T00:00:00Z",
            }
        ]
    }
    out = parse_greenhouse(data, org="Acme")
    assert len(out) == 1
    assert out[0].title == "AI Resident"
    assert out[0].posted == "2026-09-01"


def test_discover_offer_links():
    html = """
    <a href="/program/winter-2027">Apply</a>
    <a href="/about">About</a>
    <a href="https://job-boards.greenhouse.io/acme/jobs/12345">GH job</a>
    <a href="/programs">All programs</a>
    <a href="#top">top</a>
    """
    links = discover_offer_links(html, "https://acme.org/")
    assert links == ["https://acme.org/program/winter-2027"]


def test_discover_offer_links_ignores_ats_and_generic_paths():
    html = '<a href="/internships">Internships</a><a href="/residency">Residency</a><a href="/fellowship-1">F</a>'
    links = discover_offer_links(html, "https://acme.org/")
    assert "https://acme.org/internships" not in links
    assert "https://acme.org/residency" in links
    assert "https://acme.org/fellowship-1" in links


def test_valid_lever():
    data = [
        {
            "text": "Research Fellow",
            "hostedUrl": "https://lv/1",
            "descriptionPlain": "deep learning " * 30,
            "categories": {"location": "London"},
            "createdAt": 1750000000000,
        }
    ]
    out = parse_lever(data)
    assert len(out) == 1 and out[0].location == "London"
