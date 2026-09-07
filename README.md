# DocPilot

**DocPilot** is an ACL-aware document question-answering system: ingest documents, chunk, index (BM25 + vector), retrieve under access control, generate answers **with citations**, and **refuse** when evidence is insufficient or unauthorized.

> **Not DataPilot.** DataPilot is NL→SQL / data warehouse querying. DocPilot is document RAG + ACL + citations. Do not confuse the two.

## Status (Milestone B)

Implemented:

- **Markdown ingest** from `data/sample_docs/` (configurable path) with YAML frontmatter ACL fields
- **Chunking** with stable `chunk_id` / `doc_id`, source path, char offsets, section headings
- **Real BM25 index** (`rank_bm25.BM25Okapi`) persisted under `indexes/bm25/` (gitignored)
- **Vector index STUB** — clearly marked `not_real_embeddings` (no real embeddings / no fake semantic quality)
- CLI + `scripts/build_index.py` to build indexes and smoke-query BM25
- Fixture Markdown docs (labeled **FIXTURE**) including ACL frontmatter

**Not** implemented (Milestone C+): ACL-at-retrieve pipeline, generate-with-citations, refuse path end-to-end. `docpilot ask` remains a stub. PDF ingest is an honest boundary stub (skipped / raises).

No fake recall/MRR/accuracy metrics.

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
              retrieve (+ ACL filter)   ← Milestone C
                      ↓
         generate-with-citations  OR  refuse
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

## How to run (Milestone B)

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

# BM25 smoke query (prints chunk_id / path / raw scores — not eval metrics)
python -m docpilot.cli bm25-query "ACL refuse" --index-dir indexes

# tests
pytest -q
```

Indexes are written under `indexes/` (contents gitignored). Vector artifacts are stub-only and include `"not_real_embeddings": true`.

## Honest stubs

| Module | Milestone B status |
|--------|--------------------|
| `ingest.py` | Real for Markdown; PDF not implemented |
| `chunking.py` | Real |
| `index_bm25.py` | Real (`rank_bm25`) |
| `index_vector.py` | **STUB** — `not_real_embeddings` |
| `acl.py` / `retrieve.py` / `generate.py` / `refuse.py` | Still stubs (Milestone C+) |
| `cli ask` | Stub (use `bm25-query` for lexical smoke) |

## Layout

```
src/docpilot/     Python package
docs/             Architecture and design
data/sample_docs/ Fixture documents (labeled FIXTURE)
data/eval/        Eval sets (later)
indexes/          Generated indexes (gitignored contents)
tests/            Smoke / unit tests
scripts/          Helper scripts (build_index.py)
```

## License

MIT (see `pyproject.toml`).
