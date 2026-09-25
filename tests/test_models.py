from src.models import Program, load_programs, save_programs


def test_roundtrip(tmp_path):
    programs = [
        Program(org="Anthropic", title="Fellows", url="https://a", text="hello", location="Remote"),
        Program(org="OpenAI", title="Residency", url="https://b"),
    ]
    path = tmp_path / "programs.json"
    save_programs(programs, str(path))
    loaded = load_programs(str(path))
    assert [p.to_dict() for p in loaded] == [p.to_dict() for p in programs]


def test_id_is_stable_hash_of_url():
    assert Program("a", "b", "https://x").id == Program("c", "d", "https://x").id
    assert Program("a", "b", "https://x").id != Program("a", "b", "https://y").id
