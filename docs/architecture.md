# DocPilot architecture

Status: **Milestone B** — MD ingest → chunk → persistent BM25 are real; vector index is a stub marked `not_real_embeddings`. ACL retrieve / generate / refuse remain design-only until Milestone C+.

## Pipeline

```
┌─────────┐   ┌─────────┐   ┌──────────────────────┐
│ ingest  │ → │ chunk   │ → │ index_bm25 (real)    │
└─────────┘   └─────────┘   │ index_vector (STUB)  │
                            └──────────┬───────────┘
                                       ↓
                            ┌──────────────────────┐
                            │ retrieve (+ ACL)     │  ← not implemented (C)
                            └──────────┬───────────┘
                         enough evidence│
                         & authorized?  ├─ no → refuse
                                       ↓ yes
                            ┌──────────────────────┐
                            │ generate + citations │  ← not implemented (C)
                            └──────────────────────┘
```

## Stages

1. **ingest** — Load Markdown under a configurable root (`DOCPILOT_DATA_DIR` / CLI path). Parse YAML frontmatter for ACL fields. PDF is an explicit boundary (not implemented).
2. **chunk** — Split into retrieval units with stable `chunk_id`, `doc_id`, `source_path`, char offsets, and section headings when present.
3. **index (BM25 + vector)** — Lexical BM25 via `rank_bm25.BM25Okapi`, persisted under `indexes/bm25/`. Vector path writes stub metadata only (`not_real_embeddings: true`); no embedding API/model required; search returns no semantic hits.
4. **retrieve (ACL)** — Milestone C. Candidate chunks then filter by caller ACL. Not wired yet. `bm25-query` is lexical smoke only.
5. **generate-with-citations** — Milestone C.
6. **refuse** — Milestone C.

## Frontmatter / ACL metadata schema (document-level)

See README table. Normalized fields used downstream:

- `allowed_roles: list[str]` — merged from `allowed_roles`, `acl_groups`, and list-form `acl`
- `acl` — original `acl` field if present, else `{"allowed_roles": [...]}`
- `visibility`, `label`, `doc_id`, `title`, `source_path`, `body`

Chunk records inherit `allowed_roles` / `visibility` / `label` from the parent doc for later ACL-at-retrieve (not enforced in Milestone B).

## Data flow

| Stage | Input | Output | Storage |
|-------|-------|--------|---------|
| ingest | files under data dir | doc records + metadata | ephemeral → chunks |
| chunk | doc text | chunk records + doc_id | ephemeral → index |
| index BM25 | chunks | `bm25_meta.json` + `bm25_tokens.pkl` | `indexes/bm25/` |
| index vector | chunks | stub meta only | `indexes/vector/` (`not_real_embeddings`) |
| retrieve | query + caller ACL | ranked allowed chunks | Milestone C |
| generate / refuse | query + chunks | answer or refusal | Milestone C |

## Distinction from DataPilot

| | DocPilot | DataPilot |
|--|----------|-----------|
| Goal | Document Q&A + citations | NL→SQL / warehouse answers |
| Sources | Docs, FAQs, policies | Tables, SQL dialect |
| Core risk | Leak via retrieval / hallucination | Unsafe SQL / wrong metrics |
| This repo | Yes | No |

## Milestone boundary

- **A:** skeleton, README, stubs, fixture, env example.
- **B (this):** real MD ingest/chunk/BM25; vector stub with `not_real_embeddings`; BM25 smoke query CLI.
- **C+:** ACL retrieve, generate-with-citations, refuse — not started.
