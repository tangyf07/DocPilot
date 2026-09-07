# DocPilot

**DocPilot** is an ACL-aware document question-answering system: ingest documents, chunk, index (BM25 + vector), retrieve under access control, generate answers **with citations**, and **refuse** when evidence is insufficient or unauthorized.

> **Not DataPilot.** DataPilot is NL→SQL / data warehouse querying. DocPilot is document RAG + ACL + citations. Do not confuse the two.

## Status (Milestone A)

This repository currently contains a **skeleton only**:

- Package layout and stub modules (TODOs for later milestones)
- Architecture notes
- Sample fixture document (labeled FIXTURE — not production data)
- Env example and dependency lists

There is **no** working end-to-end pipeline yet. No fake metrics, no pretend demo accuracy.

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
ingest → chunk → index (BM25 + vector)
                      ↓
              retrieve (+ ACL filter)
                      ↓
         generate-with-citations  OR  refuse
```

See [docs/architecture.md](docs/architecture.md) for ACL model and data flow.

## How to run (Milestone A)

Milestone A does **not** run a real pipeline. After later milestones:

```bash
# from repo root
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill placeholders locally; never commit .env

# planned CLI (stub today):
# docpilot ingest ...
# docpilot ask "..."
```

Current CLI entry (`docpilot`) is a **stub** and will print that Milestone A is incomplete.

## Honest stubs

All modules under `src/docpilot/` except package metadata are stubs with `TODO` markers. Calling them should not claim success for unimplemented work.

## Layout

```
src/docpilot/     Python package (stubs)
docs/             Architecture and design
data/sample_docs/ Sample / fixture documents
data/eval/        Eval sets (later)
indexes/          Generated indexes (gitignored contents)
tests/            Tests (later)
scripts/          Helper scripts (later)
```

## License

MIT (see `pyproject.toml`).