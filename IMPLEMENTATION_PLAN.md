# Residence Finder Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox (`- [ ]`) syntax. Spec: `PLAN.md`.

**Goal:** Build a $0, CPU-only pipeline that discovers AI/ML residency programs, ranks them against a fixed CV, and publishes a static site.

**Architecture:** `sources.yaml` → fetch (httpx, cached, rate-limited) → extract (trafilatura / ATS JSON) → `programs.json` → hybrid match (embeddings + BM25 + skills + eligibility gate) → `ranked.json` → Jinja2 static site → GitHub Pages, refreshed weekly by Action.

**Tech Stack:** Python 3.12, httpx, trafilatura, PyYAML, fastembed (ONNX, no torch), scikit-learn, rank_bm25, numpy, Jinja2, pytest; optional Ollama.

**Spec:** `PLAN.md`

## Global Constraints

- CPU only; $0/month; no GPU, no vector DB, no backend, no web framework.
- All work under the repository root.
- CV source: `cv.tex` (or a path passed with `--tex`).
- Respect `robots.txt`; rate-limit **1 req / 2 s**; cache fetched HTML in `data/cache/`.
- Network failure, malformed source, or empty extraction **skips that source**, never crashes the run.
- No full posting text is published on the site — only scores, reasons, and links.
- Embedding model `BAAI/bge-small-en-v1.5` via fastembed; LLM default `ollama:llama3.2` (env-overridable).

## Review Focus

Each line gets a test in the owning task:

1. **Network failure mid-run** (timeout/403/DNS) → remaining sources still processed; run exits 0.
2. **Malformed HTML / ATS schema drift** → that source skipped with a logged warning; others survive.
3. **Free-text deadlines** (`"Rolling"`, `"15 Jan 2026"`, `""`) → parser filters expired correctly, never crashes.
4. **Near-empty extraction** (JS-only page) → flagged `text_len < 200`, excluded from ranking, not silently scored.
5. **Empty/tiny CV** → `match.py` raises a clear error instead of emitting garbage rankings.

## File Structure

```
residence_finder/
  data/{cv.txt,sources.yaml,skills.txt,programs.json,ranked.json,cache/,llm_cache/}
  src/{cv_to_text.py,models.py,sources.py,fetch.py,extract.py,embed.py,lexical.py,filters.py,match.py,llm.py,enrich.py,explain.py,search.py,build_site.py}
  templates/index.html.j2
  site/                      # generated
  tests/...
  requirements.txt .gitignore .github/workflows/update.yml README.md
```

---

## Phase 0 — Setup

### Task 0.1: Scaffold + dependencies
**Files:** `requirements.txt`, `.gitignore`, `src/__init__.py`, `tests/__init__.py`, `README.md`
- [x] `requirements.txt` lists runtime + test deps.
- [x] `.gitignore`: `data/cache/`, `data/llm_cache/`, `site/`, `__pycache__/`, `.venv/`, `.superpowers/`
- [x] Verify: `.venv/bin/pip install -r requirements.txt` succeeds (venv created with `--system-site-packages`).

### Task 0.2: CV → text
**Files:** `src/cv_to_text.py`, `tests/test_cv_to_text.py`; produces `data/cv.txt`
**Interfaces:** `latex_to_text(tex: str) -> str`; `main() -> None` writes `data/cv.txt`.
- [x] Test: `latex_to_text(r"\textbf{David Abert} \section{SKILLS} PyTorch")` contains `David Abert`, `PyTorch`, no `\`.
- [x] Implement: strip comments; `\cmd{...}` → `...`; drop `\begin/\end`; collapse whitespace.
- [x] Test: `main()` writes `data/cv.txt`; assert `len > 500` (**Review Focus #5**).
- [x] Commit — **skipped by ruling (no explicit commit request).**

---

## Phase 1 — Ingestion

### Task 1.1: Data model + storage
**Files:** `src/models.py`, `tests/test_models.py`
**Interfaces:** `Program(org,title,url,text,location,deadline,posted,eligibility,stipend,source,id)`; `load_programs(path)`; `save_programs(programs,path)`.
- [x] Test round-trip. Implement `to_dict`/`from_dict`; `id=sha1(url)[:16]`.

### Task 1.2: Source registry
**Files:** `data/sources.yaml`, `src/sources.py`, `tests/test_sources.py`
**Interfaces:** `load_sources(path) -> list[dict]`; `load_settings(path) -> dict`; unknown type → `ValueError`.

### Task 1.3: Cached, polite fetcher
**Files:** `src/fetch.py`, `tests/test_fetch.py`
**Interfaces:** `fetch_url(url,*,cache_dir,rate_limit_s,client_fn) -> str`; `is_allowed(url)`.
- [x] Test (**RF#1**): HTTP error → `""`, no raise. Cache hit → zero HTTP.
- [x] Implement: robots check, disk cache (TTL 24h), sleep only on live requests.

### Task 1.4: Extractors
**Files:** `src/extract.py`, `tests/test_extract.py`
**Interfaces:** `extract_text(html)`; `parse_greenhouse(json)`; `parse_lever(json)`; `parse_ashby(json)`.
- [x] Test (**RF#2**): malformed Greenhouse JSON → `[]`. (**RF#4**): empty body → `""`.

### Task 1.5: Ingest orchestrator
**Files:** `src/fetch.py` (`main`), `tests/test_ingest.py`
**Interfaces:** `dedupe(programs)`; `ingest(sources, ...)`; `main()` → `data/programs.json`.
- [x] Tests: dedupe collapse; one failing source does not stop others.

---

## Phase 2 — Matching

### Task 2.1: Local embeddings
**Files:** `src/embed.py`, `tests/test_embed.py`
**Interfaces:** `embed_texts(texts, model_name) -> np.ndarray` (L2-normalized).
- [x] Test shape + unit norm; integration similarity test (skipped offline).

### Task 2.2: Lexical + skill scoring
**Files:** `data/skills.txt`, `src/lexical.py`, `tests/test_lexical.py`
**Interfaces:** `bm25_scores(cv_text, docs) -> np.ndarray` (0–1); `skill_overlap(cv_text, doc, skills) -> float`.

### Task 2.3: Eligibility filters
**Files:** `src/filters.py`, `tests/test_filters.py`
**Interfaces:** `parse_deadline(s, today) -> date|None`; `is_eligible(program, today, cv_text) -> bool`.
- [x] Test (**RF#3**): `"Rolling"`/`""` eligible; expired → ineligible; garbage → no crash.

### Task 2.4: Ranker
**Files:** `src/match.py`, `tests/test_match.py`; produces `data/ranked.json`
**Interfaces:** `score(...)`; `rank(programs, cv_text, today, weights, embed_fn) -> list[dict]`.
- [x] Test (**RF#5**): empty CV raises `ValueError`. Eligible outranks gated.

---

## Phase 3 — LLM layer (optional)

### Task 3.1: LLM client — `src/llm.py`, `chat(system,user,model)->str`
### Task 3.2: Structured extraction — `src/enrich.py`, `extract_fields(text, chat_fn)->dict`
### Task 3.3: Rerank + explain — `src/explain.py`, `explain(cv_text, program, chat_fn)->dict` + `data/llm_cache/`

---

## Phase 4 — Static site

### Task 4.1: Templates + builder — `templates/index.html.j2`, `src/build_site.py`, `build(ranked_path,out_dir)->None`
- [x] Test: 2 fake programs → titles present, links have `noopener`.

---

## Phase 5 — Automation + discovery

### Task 5.1: Search discovery — `src/search.py`, `discover(queries, api_key)->list[str]`
### Task 5.2: GitHub Action — `.github/workflows/update.yml`
### Task 5.3: README

---

## Phase 6 — Later

Dynamic CV upload, email digest, cross-encoder reranking. Each is its own spec.
