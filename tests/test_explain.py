from src.explain import explain
from src.models import Program


def test_explain_parses_and_caches(tmp_path):
    calls = {"n": 0}

    def chat_fn(system, user):
        calls["n"] += 1
        return 'ok {"score":80,"reasons":["semantic fit"],"gaps":["no LLM papers"],"tailoring":["highlight transformers"]}'

    program = Program("O", "T", "https://x", text="python llm " * 100)
    first = explain("cv text", program, chat_fn=chat_fn, cache_dir=str(tmp_path))
    assert first["score"] == 80 and calls["n"] == 1
    second = explain("cv text", program, chat_fn=chat_fn, cache_dir=str(tmp_path))
    assert calls["n"] == 1
    assert second["reasons"] == ["semantic fit"]


def test_malformed_response_degrades(tmp_path):
    program = Program("O", "T", "https://x", text="x" * 100)
    result = explain("cv", program, chat_fn=lambda s, u: "garbage", cache_dir=str(tmp_path))
    assert result["score"] is None
    assert result["reasons"] == []
