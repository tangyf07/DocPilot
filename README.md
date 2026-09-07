# DocPilot

**DocPilot** is an ACL-aware document question-answering system: ingest documents, chunk, index (BM25 + vector), retrieve under access control, generate answers **with citations**, and **refuse** when evidence is insufficient or unauthorized.

> **Not DataPilot.** DataPilot is NL→SQL / data warehouse querying. DocPilot is document RAG + ACL + citations. Do not confuse the two.

## Status (Milestone C)

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

**Not** implemented (Milestone D+): real vector embeddings, PDF ingest, eval metrics dashboards. No fabricated accuracy/recall metrics.

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

## How to run (Milestone C)

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

## Honest stubs / status

| Module | Milestone C status |
|--------|--------------------|
| `ingest.py` | Real for Markdown; PDF not implemented |
| `chunking.py` | Real |
| `index_bm25.py` | Real (`rank_bm25`) |
| `index_vector.py` | **STUB** — `not_real_embeddings` |
| `acl.py` / `retrieve.py` | Real — ACL filter at retrieve |
| `generate.py` / `refuse.py` | Real — citations + three refuse paths |
| `cli ask` | Real — `--role` end-to-end |

## Layout

```
src/docpilot/     Python package
docs/             Architecture and design
data/sample_docs/ Fixture documents (labeled FIXTURE)
data/eval/        Eval sets (later)
indexes/          Generated indexes (gitignored contents)
tests/            Smoke / unit tests
scripts/          Helper scripts (build_index.py, demo_ask_c.py)
```

## License

MIT (see `pyproject.toml`).
