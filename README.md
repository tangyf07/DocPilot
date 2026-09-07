# DocPilot

**DocPilot** is an ACL-aware document question-answering system: ingest documents, chunk, index (BM25 + vector stub), retrieve under access control, generate answers **with citations**, and **refuse** when evidence is insufficient or unauthorized.

> **Not DataPilot.** DataPilot is NL→SQL / data warehouse querying. DocPilot is document RAG + ACL + citations. Do not confuse the two.

## Status (Milestone E / V1 closed)

Implemented (A–E):

- **Markdown ingest** from `data/sample_docs/` with YAML frontmatter ACL fields
- **Chunking** with stable `chunk_id` / `doc_id`, source path, char offsets, section headings
- **Real BM25 index** (`rank_bm25.BM25Okapi`) under `indexes/bm25/` (gitignored)
- **Vector index STUB** — `not_real_embeddings` (no real embeddings; **not** a hybrid-retrieval selling point)
- **ACL-at-retrieve** — role filter applied during retrieval (not after generation)
- **generate-with-citations** — every answer cites `chunk_id` / source; no evidence → refuse
- **refuse** — three paths: `no_hits` / `unauthorized` (ACL) / `weak_evidence`
- **CLI** `docpilot ask --role …` end-to-end
- **Degraded / no-LLM** path when `OPENAI_API_KEY` is unset (extractive citation-only; clearly labeled)
- **Milestone D eval** — GOLD fixtures (≥30) under `data/eval/`; offline runner; refuse correctness + citation coverage + optional answer heuristic (labeled heuristic, **not** accuracy). Default eval path is **DEGRADED / no-LLM**. Optional `--live-llm` is experimental and marked `not_real_api` (not production API eval). Metrics are computed from the run only — never hardcoded.
- **Milestone E interview demo** — one-shot `scripts/demo_v1.py` (ingest → authorized ask → three refuses → eval summary). CLI is enough for V1 (no web UI).

**Not** implemented (post-V1): real vector embeddings, PDF ingest, web UI / multi-tenant SaaS. No fabricated accuracy/recall metrics.

## V1 scope

| In scope | Out of scope (V1) |
|----------|-------------------|
| Local/file ingest of Markdown (and similar) | Full enterprise connector suite |
| Chunking + **BM25** index (+ vector stub only) | Real hybrid vector retrieval |
| ACL-filtered retrieval | Multi-tenant SaaS hosting |
| Answer generation with citations | NL→SQL (that is DataPilot) |
| Explicit refuse path when weak/unauthorized | Guaranteed hallucination-free answers |
| Offline GOLD eval + interview one-shot demo | Fine-tuned domain LLMs |

## Architecture overview

```
ingest → chunk → index (BM25 real + vector stub)
                      ↓
              retrieve (+ ACL filter at retrieve)
                      ↓
         generate-with-citations  OR  refuse
         (LLM if key set; else DEGRADED / no-LLM)
```

See [docs/architecture.md](docs/architecture.md) for ACL / frontmatter schema and data flow.

## Document frontmatter schema (ingest)

Optional YAML frontmatter on Markdown files:

| Field | Type | Meaning |
|-------|------|---------|
| `title` | string | Display title |
| `doc_id` | string | Stable id (default: slug of filename) |
| `allowed_roles` | list[str] | Role allow-list (preferred) |
| `acl_groups` | list[str] | Synonym; merged into `allowed_roles` |
| `acl` | list[str] or object | Alternate ACL; list merges as roles |
| `visibility` | string | e.g. `private` / `team` / `public` |
| `label` | string | Use `FIXTURE` for sample docs |

Normalized docs also carry `body`, `source_path`, `format`, `char_count`, `extra`.

## Demo (interview one-shot)

Copy-paste from repo root. Prefer the existing Windows `.venv`.

### Default: DEGRADED / no-LLM (no API key)

Screen-share friendly. Clears any `OPENAI_API_KEY` for deterministic extractive answers labeled **`DEGRADED / no-LLM`**. Retrieval is **BM25 + ACL** (vector remains a stub).

```bash
# Windows
.venv\Scripts\activate
pip install -e ".[dev]"

# One-shot: ingest/build → authorized ask → 3 refuses → GOLD eval summary
python scripts/demo_v1.py

# Faster screen-share (reuse indexes; shorter eval)
python scripts/demo_v1.py --skip-build --eval-limit 12
```

Expected outcomes in the demo stdout:

| Step | What you should see |
|------|---------------------|
| Build | `docs` / `chunks` / `bm25_size`; `not_real_embeddings=True` for vector stub |
| Authorized ask (`eng`) | `OUTCOME: answer` + `citations(chunk_id)=[...]` + `DEGRADED / no-LLM` |
| Refuse unauthorized (`contractor`) | `OUTCOME: refuse / unauthorized` |
| Refuse no hits | `OUTCOME: refuse / no_hits` |
| Refuse weak evidence | `OUTCOME: refuse / weak_evidence` |
| Eval summary | `refuse_correctness` / `citation_coverage` / `answer_heuristic` **from this run only** |

Do **not** treat printed heuristic numbers as accuracy. Do **not** sell the vector stub as hybrid retrieval.

### Optional: live LLM (API key)

Only if you have set `OPENAI_API_KEY` in `.env` or the environment. Answers may use OpenAI-compatible generation; still not a production accuracy claim.

```bash
# Keep key for ask path; eval stays DEGRADED unless --live-eval
python scripts/demo_v1.py --keep-api-key

# Experimental live eval (labeled not_real_api — NOT production API eval)
python scripts/demo_v1.py --keep-api-key --live-eval
```

### Manual CLI equivalents

```bash
python scripts/build_index.py
python -m docpilot.cli ask "What is ACL refuse behavior?" --role eng
python -m docpilot.cli ask "ACL refuse unauthorized" --role contractor
python -m docpilot.cli ask "xyzzyqwertynonexistent999zzz" --role eng
python -m docpilot.cli ask "ACL refuse" --role eng --refuse-threshold 1000
python scripts/run_eval.py
```

Milestone C-only ask demo (no eval): `python scripts/demo_ask_c.py`

## How to run (setup)

```bash
# from repo root
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill placeholders locally; never commit .env

# Build BM25 (+ vector stub marker) from fixtures
python scripts/build_index.py
# or:
python -m docpilot.cli ingest data/sample_docs --index-dir indexes

# ACL-aware ask (role required)
python -m docpilot.cli ask "What is ACL refuse behavior?" --role eng
# or: docpilot ask "..." --role eng

# Without OPENAI_API_KEY → degraded extractive / citation-only answer
# (labeled DEGRADED / no-LLM). With a key → OpenAI-compatible generation.

# Refuse demos
python -m docpilot.cli ask "ACL refuse unauthorized" --role contractor
python -m docpilot.cli ask "xyzzyqwertynonexistent999zzz" --role eng
python -m docpilot.cli ask "ACL refuse" --role eng --refuse-threshold 1000

# BM25 lexical smoke (no ACL)
python -m docpilot.cli bm25-query "ACL refuse" --index-dir indexes

# tests
pytest -q
```

Indexes are written under `indexes/` (contents gitignored). Vector artifacts are stub-only and include `"not_real_embeddings": true`.

### Degraded / no-LLM note

If `OPENAI_API_KEY` is empty or unset, `ask` still runs: it retrieves ACL-allowed chunks and returns an **extractive citation-only** answer. Output is explicitly labeled **`DEGRADED / no-LLM`**. No fabricated claims beyond retrieved excerpts.

## Offline eval (Milestone D)

Gold fixtures live in `data/eval/gold_milestone_d.jsonl` (labeled **GOLD**). Categories:

- `authorized_answer` — expect answer + `chunk_id` citations
- `unauthorized_refuse` — ACL refuse
- `no_hits_refuse` — no BM25 evidence
- `weak_evidence_refuse` — authorized hits below score threshold

**Default path = DEGRADED / no-LLM** (no API key required). Metrics printed are computed from that run only:

- `refuse_correctness` — expected refuse/ok (+ reason) vs actual
- `citation_coverage` — when answer expected, citations must include `chunk_id`
- `answer_heuristic` — simple token overlap; **labeled heuristic, not accuracy**

```bash
# ensure index exists
python scripts/build_index.py

# full offline eval (DEGRADED)
python scripts/run_eval.py
# or:
python -m docpilot.cli eval

# subset / JSON report
python scripts/run_eval.py --limit 8 --json-out indexes/eval_report.json

# optional experimental live LLM (NOT production API eval; labeled not_real_api)
python scripts/run_eval.py --live-llm

# tests (includes offline eval; no network/key)
pytest -q
pytest -q tests/test_milestone_d.py
```

Do **not** treat README or code comments as measured accuracy — only the numbers printed by a real `run_eval` / `docpilot eval` invocation.

## Honest stubs / status

| Module | V1 status |
|--------|-----------|
| `ingest.py` | Real for Markdown; PDF not implemented |
| `chunking.py` | Real |
| `index_bm25.py` | Real (`rank_bm25`) |
| `index_vector.py` | **STUB** — `not_real_embeddings` (not a hybrid selling point) |
| `acl.py` / `retrieve.py` | Real — ACL filter at retrieve |
| `generate.py` / `refuse.py` | Real — citations + three refuse paths |
| `cli ask` | Real — `--role` end-to-end |
| `eval_runner` / `cli eval` | Real — offline GOLD metrics from this run only |
| `scripts/demo_v1.py` | Real — interview one-shot (Milestone E) |

## Layout

```
src/docpilot/     Python package
docs/             Architecture and design
data/sample_docs/ Fixture documents (labeled FIXTURE)
data/eval/        GOLD eval fixtures (Milestone D)
indexes/          Generated indexes (gitignored contents)
tests/            Smoke / unit tests
scripts/          build_index.py, demo_ask_c.py, demo_v1.py, run_eval.py
```

## License

MIT (see `pyproject.toml`).
