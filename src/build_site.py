from __future__ import annotations

import json
import os
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

RANKED_PATH = "data/ranked.json"
OUT_DIR = "site"
TEMPLATE_DIR = "templates"


def _sibling(ranked_path: str, suffix: str) -> str:
    if not ranked_path.endswith(".json"):
        return ranked_path + suffix + ".json"
    return ranked_path[:-5] + suffix + ".json"


def _load(path: str) -> list[dict]:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def build(
    ranked_path: str = RANKED_PATH,
    out_dir: str = OUT_DIR,
    template_dir: str = TEMPLATE_DIR,
    reference_links: list[dict] | None = None,
    closed_path: str | None = None,
    manual_path: str | None = None,
    programs_path: str | None = None,
) -> int:
    with open(ranked_path, encoding="utf-8") as fh:
        programs = json.load(fh)
    closed = _load(closed_path or _sibling(ranked_path, "_closed"))
    manual = _load(manual_path or _sibling(ranked_path, "_manual"))
    programs_open = _load(programs_path or _sibling(ranked_path, "_programs"))
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template("index.html.j2").render(
        programs=programs,
        programs_open=programs_open,
        closed=closed,
        manual=manual,
        generated=date.today().isoformat(),
        reference_links=reference_links or [],
    )
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    return len(programs)


def main(argv: list[str] | None = None) -> None:
    import argparse

    from .sources import load_reference_links

    parser = argparse.ArgumentParser(description="Render the static site from ranked.json.")
    parser.add_argument("--ranked", default=RANKED_PATH)
    parser.add_argument("--out", default=OUT_DIR)
    parser.add_argument("--exports", default="exports")
    parser.add_argument("--closed", default=None)
    parser.add_argument("--manual", default=None)
    parser.add_argument("--open-programs", default=None)
    args = parser.parse_args(argv)

    try:
        links = load_reference_links()
    except Exception:
        links = []
    count = build(
        args.ranked, args.out, reference_links=links,
        closed_path=args.closed, manual_path=args.manual, programs_path=args.open_programs,
    )
    print(f"wrote {args.out}/index.html ({count} open offers, {len(links)} reference links)")

    from .export_recommendations import export

    stem = "recommendations" if args.ranked == RANKED_PATH else None
    rows = export(args.ranked, args.exports, stem)
    print(f"wrote {args.exports}/ (md/csv/json, {len(rows)} rows)")


if __name__ == "__main__":
    main()
