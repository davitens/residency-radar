from src.fetch import dedupe
from src.models import Program


def test_dedupe_by_url_and_name():
    a = Program("Org", "Title", "https://a")
    name_dup = Program("org", "title", "https://b")
    url_dup = Program("Other", "Other Title", "https://a")
    unique = Program("New", "New Title", "https://d")
    result = dedupe([a, name_dup, url_dup, unique])
    assert [p.title for p in result] == ["Title", "New Title"]
