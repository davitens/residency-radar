# Residence Finder — Plan

A lightweight system that discovers AI/ML residency and fellowship programs, matches them against a CV, and publishes the result as a static website.

**Owner context:** an ML researcher transitioning into LLM/ML work, looking for residencies and fellowships. Wants a lightweight tool that finds them and ranks them against a CV, with zero server maintenance.

---

## 0. Assumptions (correct these before building)

1. "Residence" = **AI/ML residency, fellowship, and research-scholar programs** aimed at career-changers / early-career researchers (Anthropic Fellows, OpenAI Residency, MATS, etc.), not medical residencies.
2. The CV is a **single fixed file** for v1 (yours). Multi-user CV upload is a later feature.
3. The site is **static** (GitHub Pages / any static host). No backend, no database, no vector DB.
4. Matching runs **offline in a scheduled job**, not in the browser.
5. Budget target: **$0/month** (local embeddings + free hosting). An LLM API key is optional and only used for explanations.

If any of those is wrong, tell me and I'll adjust before code.

---

## 1. The lazy architecture

Residency program count is tiny — likely **50–500 postings**. That number decides everything:

- **No vector database.** FAISS/Chroma/Pinecone are for millions of vectors. For 500 items a NumPy dot product is instant and free. (This is the single most common over-engineering trap here.)
- **No backend.** Matching is precomputed; the website is just HTML + a JSON file.
- **No fancy scraper cluster.** A `sources.yaml` of ~30 curated pages + public ATS JSON APIs covers the entire market better than a general crawler.

```
                 (weekly cron / GitHub Action)
sources.yaml ──► fetch ──► extract text ──► normalize ──► programs.json
                                                              │
cv.tex ──► cv.txt ──► embed ────────────────┐                 │
                                            ▼                 ▼
                                    score + rank ──► ranked.json ──► static site
                                            ▲
                                    optional LLM rerank/explain
```

**Deliverable:** `index.html` reads `ranked.json` and renders a sortable table (program, org, score, why-match, deadline, link).

### Repo layout

```
residence_finder/
  data/
    cv.txt              # plain text extracted from cv.tex
    sources.yaml        # direct program sources + reference links + search queries
    programs.json       # raw normalized postings
    ranked.json         # generated: programs + scores + explanations
  src/
    cv_to_text.py       # .tex/.pdf -> text
    fetch.py            # pull sources -> programs.json
    extract.py          # HTML -> clean text (trafilatura)
    embed.py            # local fastembed (ONNX) embeddings, no PyTorch
    match.py            # hybrid scoring -> ranked.json
    build_site.py       # jinja2 render -> site/
  site/                 # generated static output
  requirements.txt
  .github/workflows/update.yml
```

---

## 2. Where to find programs

Two layers: **curated seeds** (reliable) and **discovery** (search + ATS APIs).

### 2.1 Curated seed sources (start here)

Aggregators / job boards — one page each, high signal:

| Source | URL | Notes |
|---|---|---|
| 80,000 Hours job board (AI safety/research filter) | 80000hours.org/job-board/ | Best single aggregator for AI safety fellowships/residencies |
| AI Safety / alignment job boards | aisafety.info, aialignment.org | Community-maintained lists |
| Euraxess | euraxess.ec.europa.eu/jobs | EU-funded research positions + fellowships |
| Academic Positions | academicpositions.com | EU/global academic research jobs |
| FindAPhD / FindAMasters | findaphd.com | Funded PhDs and research posts |
| Nature Careers | nature.com/naturecareers | Research fellowships |

Direct program pages (these move/retire yearly — verify):

| Program | Org | URL |
|---|---|---|
| Anthropic Fellows Program | Anthropic | anthropic.com/careers |
| OpenAI Residency | OpenAI | openai.com/residency |
| MATS (ML Alignment Theory Scholars) | MATS | matsprogram.org |
| AI Safety Camp | AISC | aisafety.camp |
| Cohere For AI Scholars | Cohere | cohere.com/research |
| ERA Fellowship | Existential Risk Alliance | existentialriskalliance.org |
| Nonlinear Fellowships | Nonlinear | nonlinear.org |
| FAR AI | FAR AI | far.ai |
| Redwood Research | Redwood | redwoodresearch.org |
| Apollo Research | Apollo | apolloresearch.ai |
| EleutherAI | EleutherAI | eleuther.ai |
| AI2 / Allen Institute | AI2 | allenai.org |
| Google DeepMind careers | Google | deepmind.google/about/careers/ |
| Microsoft Research careers | Microsoft | microsoft.com/en-us/research/careers/ |
| Mila / Vector Institute | Mila / Vector | mila.quebec, vectorinstitute.ai |
| Recurse Center | Recurse | recurse.com |
| La Caixa INPhINIT (Spain, relevant to you) | La Caixa | lacaixafellowships.org |
| Marie Skłodowska-Curie Actions | EU | marie-sklodowska-curie-actions.ec.europa.eu |
| Hugging Face jobs | HF | huggingface.co/jobs |

> These URLs are from memory and drift over time. Run `python -m src.check_sources` after edits; `sources.yaml` is the source of truth, so dead links cost nothing but a deleted line.
>
> Aggregators that can't be cleanly parsed (80k Hours, Euraxess, …) live under `reference_links:` and render as an unranked "Job boards to check" list. Ranked `page` sources should point at a specific program and carry `org:`/`title:`. ATS feeds (Greenhouse/Ashby/Lever) are filtered to residency/fellowship titles before ranking (`filters.is_residency`), and their structured fields (`deadline`/`location`/`eligibility`/`stipend`) are filled by the Ollama enrichment step during `src.fetch`.

### 2.2 Discovery via search

A handful of queries, run through a search API, harvested for new program URLs:

```yaml
queries:
  - '"AI residency" OR "research residency" 2026'
  - '"AI safety fellowship" applications'
  - '"machine learning" "residency program" -site:reddit.com'
  - '"research fellowship" LLM alignment funded'
```

Search backends (pick one): **Brave Search API** (free tier, good), **Bing Web Search API**, or DuckDuckGo HTML (free but brittle). Add newly found domains to `sources.yaml` after a human glance — a human-in-the-loop step keeps this lazy and accurate.

### 2.3 Discovery via ATS public APIs (no scraping!)

Most AI orgs post jobs through Greenhouse / Lever / Ashby / Workable, and those expose **public JSON endpoints**. This is far more robust than scraping HTML:

```
https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
https://api.lever.co/v0/postings/{company}?mode=json
https://api.ashbyhq.com/posting-api/job-board/{company}
https://apply.workable.com/api/v1/widget/accounts/{company}
```

Add a `company` slug and fetch structured JSON directly. Start with orgs you already care about; no HTML parsing, no selectors to break.

---

## 3. Scraping / ingestion

### Steps

1. **Load** `sources.yaml` — each entry: `name`, `type` (`page` | `greenhouse` | `lever` | `ashby`), `url`/`slug`, optional `selector`.
2. **Fetch** with `httpx` (timeout, retry, 1 req/2s, honest `User-Agent`).
3. **Extract** main content with [`trafilatura`](https://github.com/adbar/trafilatura) — purpose-built for news/article/program pages, strips nav/ads/footers. Fall back to `readability-lxml` for stubborn sites.
4. **Normalize** into one schema.
5. **Deduplicate** by URL and by `(org, title)` after lowercasing.
6. **Persist** to `programs.json`.

### Normalized schema

```json
{
  "id": "sha1(url)",
  "org": "Anthropic",
  "title": "Anthropic Fellows Program",
  "url": "https://...",
  "text": "full cleaned description ...",
  "location": "Remote / London",
  "deadline": "2026-01-15",
  "posted": "2026-09-01",
  "eligibility": "career-changers, PhD not required",
  "stipend": "yes",
  "source": "curated"
}
```

### Robots / etiquette

- Respect `robots.txt` (`urllib.robotparser`).
- Rate-limit, cache fetched HTML on disk for a day (so re-runs are free and won't re-hit sites).
- Prefer APIs and RSS over HTML when available.
- This is personal-scale ingestion, not a public crawler.

### Algorithm note

Ingestion is intentionally **rule-based, not ML**. Text extraction and API parsing are solved problems; throwing an LLM at HTML parsing is slower, costlier, and less reliable.

---

## 4. Matching CV ↔ program

Three layers, cheapest first. Combine into one score.

### Layer 1 — Hard filters (boolean gate)

Cut before scoring. From the posting, extract or hand-annotate:

- Degree requirement (PhD / MSc / none)
- Location & remote policy (you're in Spain, willing to relocate)
- Citizenship/visa restrictions
- Deadline not passed
- Funding available (unfunded "residencies" are usually a red flag)

Extraction method: regex + keyword rules first (`"PhD required"`, `"remote"`, `"must be authorized"`). Only escalate to an LLM if rules prove too weak.

### Layer 2 — Semantic similarity (dense embeddings)

The core NLP signal, and it's free and local:

```python
from fastembed import TextEmbedding
model = TextEmbedding("BAAI/bge-small-en-v1.5")  # ~130MB, ONNX, CPU, no PyTorch
sim = cosine(embed(cv_text), embed(program_text))
```

Why this beats keyword overlap: a CV says "uncertainty quantification, time-series forecasting, PyTorch", a posting says "probabilistic ML, sequence models, deep learning" — zero shared words, high semantic match. Embeddings bridge that vocabulary gap, which is exactly the domain-transition problem.

### Layer 3 — Lexical / skill overlap (complementary signal)

Embeddings miss exact must-haves (e.g. posting requires "PyTorch" or "publications"). Add:

- **TF-IDF + cosine** or **BM25** (`rank_bm25`) over CV vs posting.
- **Skill dictionary overlap**: maintain `skills.txt` (python, pytorch, transformers, LLM, NLP, publications, causal inference, MLOps, ...). Score = weighted Jaccard of matched skills; weight rare skills higher (IDF).

### Combined score

```
score = 0.55 * embedding_sim      # semantic fit
      + 0.25 * bm25_norm          # keyword fit
      + 0.15 * skill_overlap      # explicit must-haves
      + 0.05 * recency_bonus      # newer postings rank higher
# then multiply by eligibility gate (0/1) from Layer 1
```

Weights are a starting point — tune them by eyeballing the top 20 (there's no ground-truth labels; don't build an ML ranker for 200 items).

### Optional Layer 4 — LLM re-rank + explanation

For the **top 15–20 only** (cost control), ask an LLM to score and explain. This turns a number into something a human can act on, and doubles as your hands-on LLM practice.

```
System: You assess fit between a candidate CV and a research program.
Return JSON: { "score": 0-100, "reasons": [..], "gaps": [..], "tailoring": [..] }

User:
CV: {cv_text}
PROGRAM: {program_text}
```

Use **Ollama locally** (`llama3.2` by default) for $0, or an API (Claude/GPT/Gemini) for quality. Cache results keyed by `hash(cv + program)` so re-runs cost nothing. Force JSON output (`format: json` for Ollama, `response_format` for OpenAI-compatible) so parsing is reliable.

> This is also your on-ramp: the LLM extraction/rerank code **is** applied LLM work you can show in interviews. Prompt engineering, structured output, caching, evaluation — real skills.

---

## 5. Website (lightweight)

**Static JSON + one HTML page.** That's it.

- `build_site.py` renders `site/index.html` from `ranked.json` (Jinja2) or ships a tiny vanilla-JS table that fetches the JSON.
- Columns: Program, Org, Match score, Why match (LLM), Gaps, Deadline, Apply link.
- Controls: sort by score/deadline, filter by location/remote/funding, search box.
- Deploy: GitHub Pages (or Netlify/Cloudflare Pages) — free, no server.

### When to add a backend (only if needed)

If you later want "paste any CV and get matches" for other people, add a small **FastAPI** endpoint or a serverless function that runs the same `match.py` on an uploaded CV. Until then, a backend is pure cost. Don't build it in v1.

---

## 6. Automation

`.github/workflows/update.yml`, weekly:

```yaml
on:
  schedule: [{ cron: "0 6 * * 1" }]   # Mondays 06:00
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: python src/fetch.py && python src/match.py && python src/build_site.py
      - run: git diff --quiet || git commit -am "chore: refresh programs"
      # push / deploy Pages
```

Free, serverless, and you get the site without lifting a finger.

---

## 7. Build order (milestones)

| Phase | Goal | Output | Est. |
|---|---|---|---|
| **0. Setup** | Repo, `requirements.txt`, `cv_to_text.py` (LaTeX → txt) | `cv.txt` | 0.5 day |
| **1. Ingest** | `sources.yaml` (10 sources), `fetch.py`, `extract.py` | `programs.json` | 1–2 days |
| **2. Match v1** | Embeddings + BM25 + skill overlap | `ranked.json` | 1 day |
| **3. LLM layer** | Structured field extraction + top-20 explanations (Ollama) | `ranked.json` w/ reasons | 1–2 days |
| **4. Site** | `build_site.py`, static page, local preview | working site | 1 day |
| **5. Automate** | GitHub Action, Pages deploy, search-based discovery | live site | 0.5 day |
| **6. Stretch** | Dynamic CV upload, more sources, email digest | — | later |

Phases 1–2 are the minimum useful product. Stop after Phase 4 if you just want a tool for yourself.

---

## 8. Stack

```
httpx              # fetching
trafilatura        # HTML -> clean text
beautifulsoup4     # fallback parsing
pyyaml             # sources.yaml
fastembed          # local ONNX embeddings (CPU, no PyTorch)
rank_bm25          # lexical ranking
numpy              # the "vector DB"
pypdf              # PDF CV fallback (pdftotext preferred)
jinja2             # static site render
# optional:
ollama             # local LLM enrichment + rerank (llama3.2)
```

No PyTorch training, no GPU, no vector DB, no web framework. Runs on a laptop and on a free CI runner.

---

## 9. Honest risks / notes

- **Scraping brittleness**: rely on ATS JSON + curated sources; treat search-derived URLs as candidates for review.
- **No labels for ranking**: tune weights by inspection; don't over-fit a model.
- **Program pages churn**: many fellowships open seasonally; weekly refresh + deadline filter handles it.
- **Legal/ToS**: personal use, rate-limited, `robots.txt`-respecting, prefer public APIs. Don't republish full posting text publicly — link to the source.
- **LLM hallucination in explanations**: keep the original posting link next to every score; treat reasons as hints, not facts.

---

## 10. What this gives *you* beyond a tool

Each component is directly relevant LLM/ML experience for your residency applications:

- Text extraction + structured data pipelines (data engineering)
- Embedding-based retrieval + hybrid ranking (core RAG infrastructure)
- Prompt engineering, structured output, caching, cost control (applied LLM)
- Static deployment + CI automation (MLOps)
- A live, linkable project that shows initiative in exactly the field you're targeting

---

*Next step: confirm the assumptions in §0, then I'll scaffold Phase 0–1.*
