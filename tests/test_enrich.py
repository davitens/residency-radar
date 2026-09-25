from src.enrich import enrich_program, extract_fields, first_json
from src.models import Program


def test_first_json_handles_wrapping_and_nesting():
    assert first_json('here: {"a": 1, "b": {"c": 2}} done') == {"a": 1, "b": {"c": 2}}
    assert first_json("no json here") == {}
    assert first_json('{"s": "a } b"}') == {"s": "a } b"}


def test_extract_fields_from_markdown():
    def chat_fn(system, user):
        return 'Sure!\n```json\n{"deadline":"2026-01-15","location":"Remote","eligibility":"","stipend":"yes"}\n```'

    fields = extract_fields("some posting text", chat_fn)
    assert fields["deadline"] == "2026-01-15"
    assert fields["location"] == "Remote"


def test_extract_fields_degrades_gracefully():
    assert extract_fields("posting", lambda s, u: "no json") == {}
    assert extract_fields("", lambda s, u: "{}") == {}


def test_extract_fields_cache_hit(tmp_path):
    calls = {"n": 0}

    def chat_fn(system, user):
        calls["n"] += 1
        return '{"deadline":"2026-01-15","location":"Remote","eligibility":"","stipend":"yes"}'

    first = extract_fields("some posting text", chat_fn, cache_dir=str(tmp_path))
    second = extract_fields("some posting text", chat_fn, cache_dir=str(tmp_path))
    assert first == second
    assert calls["n"] == 1


def test_enrich_program_sets_and_preserves(tmp_path):
    good = Program("O", "T", "https://a", text="x" * 300)
    enrich_program(
        good,
        chat_fn=lambda s, u: '{"deadline":"2026-05-01","location":"Remote","eligibility":"open","stipend":"yes"}',
        cache_dir=str(tmp_path),
    )
    assert good.deadline == "2026-05-01" and good.location == "Remote"

    failing = Program("O", "T", "https://b", text="different text " * 40, deadline="keep")
    enrich_program(failing, chat_fn=lambda s, u: "garbage", cache_dir=str(tmp_path))
    assert failing.deadline == "keep"


def test_enrich_program_normalizes_status(tmp_path):
    program = Program("O", "T", "https://c", text="status text " * 40)
    enrich_program(
        program,
        chat_fn=lambda s, u: '{"status":"Closed","status_evidence":"applications are closed"}',
        cache_dir=str(tmp_path),
    )
    assert program.status == "closed"
    assert program.status_evidence == "applications are closed"

    weird = Program("O", "T", "https://d", text="other text " * 40)
    enrich_program(weird, chat_fn=lambda s, u: '{"status":"maybe"}', cache_dir=str(tmp_path))
    assert weird.status == "unknown"
