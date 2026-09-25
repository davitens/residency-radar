import json

from src.build_site import build


def test_build_renders_programs(tmp_path):
    ranked = [
        {"title": "A Program", "org": "OrgA", "url": "https://a", "score": 0.9,
         "deadline": "2026-12-01", "location": "Remote", "reasons": ["fit"], "gaps": ["no LLM"]},
        {"title": "B Program", "org": "OrgB", "url": "https://b", "score": 0.5},
    ]
    ranked_path = tmp_path / "ranked.json"
    ranked_path.write_text(json.dumps(ranked), encoding="utf-8")
    count = build(
        str(ranked_path),
        str(tmp_path / "site"),
        "templates",
        reference_links=[{"name": "Euraxess jobs", "url": "https://euraxess.test/"}],
    )
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert count == 2
    assert "A Program" in html and "B Program" in html
    assert "noopener" in html
    assert "0.900" in html
    assert "Euraxess jobs" in html


def test_build_renders_closed_watchlist(tmp_path):
    ranked_path = tmp_path / "ranked.json"
    ranked_path.write_text("[]", encoding="utf-8")
    (tmp_path / "ranked_closed.json").write_text(
        json.dumps(
            [{"title": "MATS closed", "url": "https://m.test/", "org": "MATS",
              "status_evidence": "applications are now closed", "status": "closed"}]
        ),
        encoding="utf-8",
    )
    build(str(ranked_path), str(tmp_path / "site"), "templates")
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "Closed / watchlist" in html
    assert "MATS closed" in html


def test_build_renders_open_programs(tmp_path):
    ranked_path = tmp_path / "ranked.json"
    ranked_path.write_text("[]", encoding="utf-8")
    (tmp_path / "ranked_programs.json").write_text(
        json.dumps([{"title": "AI Safety Camp", "url": "https://camp.test/", "org": "AISC",
                     "status": "open", "score": 0.5}]),
        encoding="utf-8",
    )
    build(str(ranked_path), str(tmp_path / "site"), "templates")
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "Open programs (apply anytime)" in html
    assert "AI Safety Camp" in html


def test_build_renders_manual_programs(tmp_path):
    ranked_path = tmp_path / "ranked.json"
    ranked_path.write_text("[]", encoding="utf-8")
    (tmp_path / "ranked_manual.json").write_text(
        json.dumps([{"title": "CHAI Program", "url": "https://chai.test/", "org": "CHAI", "status": "unknown"}]),
        encoding="utf-8",
    )
    build(str(ranked_path), str(tmp_path / "site"), "templates")
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "without a specific open posting" in html
    assert "CHAI Program" in html
