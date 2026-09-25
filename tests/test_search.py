from src.search import discover, filter_known


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


def test_discover_dedupes():
    data = {"web": {"results": [{"url": "https://a.com/1"}, {"url": "https://a.com/1"}, {"url": "https://b.com/2"}]}}
    urls = discover(["q"], api_key="k", client_fn=lambda url, params, headers: FakeResponse(data))
    assert urls == ["https://a.com/1", "https://b.com/2"]


def test_discover_without_key_is_empty():
    assert discover(["q"], api_key="") == []


def test_filter_known_domains():
    known = {"matsp.org", "anthropic.com"}
    urls = ["https://www.matsp.org/x", "https://new.ai/y", "https://anthropic.com/jobs"]
    assert filter_known(urls, known) == ["https://new.ai/y"]
