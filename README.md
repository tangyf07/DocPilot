# DocPilot

**DocPilot** is an ACL-aware document question-answering system: ingest documents, chunk, index (BM25 + vector), retrieve under access control, generate answers **with citations**, and **refuse** when evidence is insufficient or unauthorized.

> **Not DataPilot.** DataPilot is NL→SQL / data warehouse querying. DocPilot is document RAG + ACL + citations. Do not confuse the two.

## Status (Milestone D)

Implemented:

- **Markdown ingest** from `data/sample_docs/` with YAML frontmatter ACL fields
- **Chunking** with stable `chunk_id` / `doc_id`, source path, char offsets, section headings
- **Real BM25 index** (`rank_bm25.BM25Okapi`) under `indexes/bm25/` (gitignored)
- **Vector index STUB** — `not_real_embeddings` (no real embeddings)
- **ACL-at-retrieve** — role filter applied during retrieval (not after generation)
- **generate-with-citations** — every answer cites `chunk_id` / source; no evidence → refuse
- **refuse** — three paths: `no_hits` / `unauthorized` (ACL) / `weak_evidence`
- **CLI** `docpilot ask --role …` end-to-end
- **Degraded / no-LLM** path when `OPENAI_API_KEY` is unset (extractive citation-only; clearly labeled)
- **Milestone D eval** — GOLD fixtures (≥30) under `data/eval/`; offline runner; refuse correctness + citation coverage + optional answer heuristic (labeled heuristic, not accuracy). Default eval path is **DEGRADED / no-LLM**. Optional `--live-llm` is experimental and marked `not_real_api` (not production API eval). Metrics are computed from the run only — never hardcoded.

**Not** implemented (later): real vector embeddings, PDF ingest, web UI / interview demo (Milestone E not started). No fabricated accuracy/recall metrics.

## V1 scope (planned)

| In scope | Out of scope (V1) |
|----------|-------------------|
| Local/file ingest of Markdown (and similar) | Full enterprise connector suite |
| Chunking + BM25 + vector hybrid index | Multi-tenant SaaS hosting |
| ACL-filtered retrieval | NL→SQL (that is DataPilot) |
| Answer generation with citations | Guaranteed hallucination-free answers |
| Explicit refuse path when weak/unauthorized | Fine-tuned domain LLMs |

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

## How to run (Milestone C/D)

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

# Demo script (all paths)
python scripts/demo_ask_c.py

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

| Module | Milestone D status |
|--------|--------------------|
| `ingest.py` | Real for Markdown; PDF not implemented |
| `chunking.py` | Real |
| `index_bm25.py` | Real (`rank_bm25`) |
| `index_vector.py` | **STUB** — `not_real_embeddings` |
| `acl.py` / `retrieve.py` | Real — ACL filter at retrieve |
| `generate.py` / `refuse.py` | Real — citations + three refuse paths |
| `cli ask` | Real — `--role` end-to-end |
| `eval_runner` / `cli eval` | Real — offline GOLD metrics from this run only |

## Layout

```
src/docpilot/     Python package
docs/             Architecture and design
data/sample_docs/ Fixture documents (labeled FIXTURE)
data/eval/        GOLD eval fixtures (Milestone D)
indexes/          Generated indexes (gitignored contents)
tests/            Smoke / unit tests
scripts/          Helper scripts (build_index.py, demo_ask_c.py, run_eval.py)
```

## License

MIT (see `pyproject.toml`).
