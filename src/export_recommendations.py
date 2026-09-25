from __future__ import annotations

import csv
import json
import os

EXPORT_DIR = "exports"


def _rows(ranked: list[dict]) -> list[dict]:
    return [
        {
            "rank": i,
            "name": p.get("title", ""),
            "source": p.get("url", ""),
            "score": round(float(p.get("score", 0.0)), 4),
            "status": p.get("status", "unknown"),
        }
        for i, p in enumerate(ranked, 1)
    ]


def export(ranked_path: str, out_dir: str = EXPORT_DIR, stem: str | None = None) -> list[dict]:
    with open(ranked_path, encoding="utf-8") as fh:
        ranked = json.load(fh)
    rows = _rows(ranked)
    stem = stem or os.path.splitext(os.path.basename(ranked_path))[0]
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, stem + ".json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)

    with open(os.path.join(out_dir, stem + ".csv"), "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["rank", "name", "source", "score", "status"])
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        f"# Recommendations ({len(rows)})",
        "",
        "| # | Name | Source | Score | Status |",
        "|---|------|--------|-------|--------|",
    ]
    lines += [
        f"| {r['rank']} | {r['name']} | {r['source']} | {r['score']:.4f} | {r['status']} |" for r in rows
    ]
    with open(os.path.join(out_dir, stem + ".md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return rows


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Export ranked recommendations to md/csv/json.")
    parser.add_argument("--ranked", default="data/ranked.json")
    parser.add_argument("--out", default=EXPORT_DIR)
    parser.add_argument("--stem", default=None)
    args = parser.parse_args(argv)
    rows = export(args.ranked, args.out, args.stem)
    stem = args.stem or os.path.splitext(os.path.basename(args.ranked))[0]
    print(f"wrote {args.out}/{stem}.{{md,csv,json}} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
