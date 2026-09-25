import pytest

from src.sources import load_reference_links, load_settings, load_sources


def test_load_sources(tmp_path):
    path = tmp_path / "s.yaml"
    path.write_text(
        "settings:\n  rate_limit_s: 1.5\nsources:\n"
        "  - {name: A, type: page, url: 'https://a'}\n"
        "  - {name: B, type: greenhouse, slug: acme}\n",
        encoding="utf-8",
    )
    sources = load_sources(str(path))
    assert [s["name"] for s in sources] == ["A", "B"]
    assert load_settings(str(path))["rate_limit_s"] == 1.5


def test_load_reference_links(tmp_path):
    path = tmp_path / "s.yaml"
    path.write_text(
        "sources: []\nreference_links:\n  - {name: A, url: 'https://a'}\n", encoding="utf-8"
    )
    assert load_reference_links(str(path)) == [{"name": "A", "url": "https://a"}]


def test_unknown_type_raises(tmp_path):
    path = tmp_path / "s.yaml"
    path.write_text("sources:\n  - {name: A, type: weird, url: 'https://a'}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_sources(str(path))
