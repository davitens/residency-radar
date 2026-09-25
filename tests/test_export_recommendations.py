import csv
import json

from src.export_recommendations import export


def test_export_writes_md_csv_json(tmp_path):
    ranked = [
        {"title": "MATS Program", "url": "https://mats.test/", "score": 0.6412},
        {"title": "AI Safety Camp", "url": "https://camp.test/", "score": 0.435},
    ]
    ranked_path = tmp_path / "ranked_example.json"
    ranked_path.write_text(json.dumps(ranked), encoding="utf-8")

    rows = export(str(ranked_path), out_dir=str(tmp_path / "exports"))
    assert rows[0] == {
        "rank": 1,
        "name": "MATS Program",
        "source": "https://mats.test/",
        "score": 0.6412,
        "status": "unknown",
    }

    out = tmp_path / "exports"
    data = json.loads((out / "ranked_example.json").read_text(encoding="utf-8"))
    assert [r["rank"] for r in data] == [1, 2]

    with open(out / "ranked_example.csv", encoding="utf-8") as fh:
        parsed = list(csv.DictReader(fh))
    assert parsed[0]["name"] == "MATS Program"
    assert parsed[0]["source"] == "https://mats.test/"

    md = (out / "ranked_example.md").read_text(encoding="utf-8")
    assert "| 1 | MATS Program | https://mats.test/ | 0.6412 | unknown |" in md
    assert "| 2 | AI Safety Camp |" in md
