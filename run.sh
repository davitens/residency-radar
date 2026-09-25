#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python
[ -x "$PY" ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }

CV=$(ls cv/*.pdf cv/*.tex 2>/dev/null | head -n1) || true
[ -n "${CV:-}" ] || { echo "no CV found in cv/ — put a .pdf or .tex there" >&2; exit 1; }

"$PY" -m src.cv_to_text --tex "$CV" --out data/cv.txt
"$PY" -m src.fetch
"$PY" -m src.match
"$PY" -m src.build_site

echo
echo "done -> site/index.html  (serve: $PY -m http.server -d site 8000)"
