# Residency Radar

**Find open AI/ML residencies and fellowships, ranked against your CV — and publish the result as a static site.**

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![No GPU](https://img.shields.io/badge/GPU-not%20required-success.svg)](#)
[![No backend](https://img.shields.io/badge/backend-none-lightgrey.svg)](#)

The AI/ML residency and fellowship market is scattered across lab pages, ATS job boards and annual
cohort cycles — and generic "open positions" pages are usually stale landing pages, not actual offers.
Residency Radar harvests **specific offer pages**, checks whether each program is **currently open**,
scores everything against a CV, and separates the results into honest buckets.

CPU-only. No GPU. No backend. No vector database. No paid APIs required.

---

## What you get

Four clearly separated lists, so you never mistake a landing page for an open offer:

| Bucket | Meaning | Output |
|---|---|---|
| **Ranked** | specific, currently-open offers | `data/ranked.json` |
| **Open programs** | flexible programs with no specific posting, but explicitly open | `data/ranked_programs.json` |
| **Manual / unknown** | status could not be determined | `data/ranked_manual.json` |
| **Closed / watchlist** | closed cohorts, kept with evidence for when they reopen | `data/ranked_closed.json` |

…plus a static site (`site/index.html`) and exports in `exports/` (Markdown, CSV, JSON).

## How it works

```
data/sources.yaml ──► fetch ──► extract text ──► offer discovery ──► programs.json
      (page / ATS)      │            │                 │
                        │       trafilatura      /apply, /residency,
                        │                        /fellowship, ATS feeds
                        ▼
                  robots.txt + 1 req/2s + 24h cache
                                                     │
cv.tex ──► cv.txt ──► embeddings ────────────────────┤
                        (fastembed, ONNX)            ▼
                                              hybrid scoring ──► ranked.json
                                        embeddings + BM25 + skills + recency
                                                     │
                                          status gating (open/closed)
                                                     │
                                        optional local LLM enrichment
                                          (deadlines, eligibility, why/gaps)
                                                     ▼
                                          static site + md/csv/json exports
```

### Matching

```
score = 0.55·semantic + 0.25·BM25 + 0.15·skills + 0.05·recency
```

- **Semantic** — `BAAI/bge-small-en-v1.5` embeddings via `fastembed` (ONNX, no PyTorch), cosine similarity.
- **BM25** — lexical overlap (`rank_bm25`), normalised per run.
- **Skills** — recall of CV skills (`data/skills.txt`) mentioned in the posting.
- **Recency** — newer postings score higher.
- **Gates** — expired deadlines, "PhD required" when absent, US-work-authorization requirements the CV lacks.
- **Residency filter** — ATS postings are filtered to residency/fellowship/scholar titles; curated sources pass.

### Open / closed detection

`src/status.py` is rule-first (cheap, deterministic) with an optional local-LLM fallback:

- ATS postings → `open`
- future deadline → `open`, past deadline → `closed`
- phrases like *"applications are now closed"*, *"no longer accepting"* → `closed`
- *"applications are open"*, *"apply by"*, *"rolling"* → `open` / `rolling`
- anything else → `unknown` (routed to the manual list)

## Quickstart

```bash
git clone git@github.com:davitens/residency-radar.git
cd residency-radar

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 1. Put your CV at ./cv.tex (LaTeX) or ./cv.pdf, then extract it to text
.venv/bin/python -m src.cv_to_text              # -> data/cv.txt
#    or: .venv/bin/python -m src.cv_to_text --tex /path/to/cv.pdf --out data/cv.txt

# 2. Discover programs -> data/programs.json
#    (optional LLM enrichment of deadline/location/eligibility/status when Ollama is running;
#     set ENABLE_ENRICH=0 to skip)
.venv/bin/python -m src.fetch

# 3. Rank against the CV -> data/ranked*.json
.venv/bin/python -m src.match
#    with LLM why/gaps (top 20):  ENABLE_LLM=1 .venv/bin/python -m src.match

# 4. Build the site + exports -> site/index.html, exports/recommendations.{md,csv,json}
.venv/bin/python -m src.build_site
.venv/bin/python -m http.server -d site 8000    # http://localhost:8000
```

Run a second CV without clobbering the first:

```bash
.venv/bin/python -m src.match --cv other_cv.txt --out data/ranked_other.json
.venv/bin/python -m src.build_site --ranked data/ranked_other.json --out site_other
```

## Tests

```bash
.venv/bin/python -m pytest -q -m "not integration"   # fast, offline
.venv/bin/python -m pytest -q                        # includes model download/network tests
```

## Adding sources

Everything lives in `data/sources.yaml`. Four source types:

- `page` — fetch and extract a program page (set `org`, `title`, and optionally `offer_links`).
- `greenhouse` / `lever` / `ashby` — public ATS JSON (`slug`), giving specific active offers.

```yaml
- name: "MATS"
  type: page
  url: "https://www.matsprogram.org/"
  org: "MATS"
  title: "ML Alignment Theory Scholars (MATS)"
  offer_links: ["https://www.matsprogram.org/residency"]   # exact offer/apply page(s)
```

- `offer_links: [...]` — pin the specific offer/apply page(s).
- `offer_links: []` — the program has no separate offer page; rank the program page itself as an
  *open program* if it is open.
- omit `offer_links` — auto-discover same-domain `/apply`, `/residency`, `/fellowship`, `/program/<x>` links.

Aggregators and portals that can't be cleanly parsed go under `reference_links:` and render as a
*Job boards to check* list on the site. Verify your sources after editing:

```bash
.venv/bin/python -m src.check_sources
```

## Configuration

| Env var | Purpose |
|---|---|
| `ENABLE_ENRICH=0` | Disable LLM field extraction during `src.fetch` |
| `ENABLE_LLM=1` | Add LLM "why / gaps" explanations for the top 20 in `src.match` |
| `LLM_PROVIDER` | `ollama` (default) or any OpenAI-compatible provider |
| `LLM_MODEL` | model name, default `llama3.2` |
| `OLLAMA_URL` | Ollama daemon, default `http://localhost:11434` |
| `LLM_BASE_URL`, `LLM_API_KEY` | OpenAI-compatible endpoint |
| `BRAVE_API_KEY` | enables `python -m src.search` source discovery |

Tune the score weights in `src/match.py` (`WEIGHTS`) and the eligibility gates in `src/filters.py`.

## Project layout

```
data/        sources.yaml, skills.txt   (generated data is gitignored)
src/         cv_to_text, models, sources, fetch, extract, status, embed, lexical,
             filters, match, llm, enrich, explain, search, check_sources,
             build_site, export_recommendations
templates/   index.html.j2
tests/
site/  exports/  data/*.json             (generated)
```

## Automation

`.github/workflows/update.yml` is a Pages-deploy template. It needs a CV in the repo (or a secret),
so it is set to `workflow_dispatch` only; uncomment the `schedule` trigger once `cv.tex` is available
in CI.

## Ethics

Personal-scale, polite ingestion: `robots.txt` is respected, requests are rate-limited to 1/2s, and
responses are cached for 24h. The site links to original postings and never republishes full posting
text.

## License

MIT — see [LICENSE](LICENSE).
