# DocPilot architecture

Status: **Milestone C** — MD ingest → chunk → BM25, ACL-at-retrieve, generate-with-citations, refuse, and `ask --role` are implemented. Vector index remains a stub marked `not_real_embeddings`.

## Pipeline

```
┌─────────┐   ┌─────────┐   ┌──────────────────────┐
│ ingest  │ → │ chunk   │ → │ index_bm25 (real)    │
└─────────┘   └─────────┘   │ index_vector (STUB)  │
                            └──────────┬───────────┘
                                       ↓
                            ┌──────────────────────┐
                            │ retrieve (+ ACL)     │  ← filter at retrieve
                            └──────────┬───────────┘
                         enough evidence│
                         & authorized?  ├─ no → refuse
                                       ↓ yes
                            ┌──────────────────────┐
                            │ generate + citations │  ← LLM or DEGRADED/no-LLM
                            └──────────────────────┘
```

## Stages

1. **ingest** — Load Markdown under a configurable root. Parse YAML frontmatter for ACL fields. PDF is an explicit boundary (not implemented).
2. **chunk** — Split into retrieval units with stable `chunk_id`, `doc_id`, `source_path`, char offsets, section headings; inherit `allowed_roles`.
3. **index (BM25 + vector)** — Lexical BM25 via `rank_bm25.BM25Okapi` under `indexes/bm25/`. Vector path writes stub metadata only (`not_real_embeddings: true`).
4. **retrieve (ACL)** — BM25 candidates, then **ACL filter at retrieve time** (not post-generation). Returns only role-allowed chunks; records `acl_dropped` / `raw_count`.
5. **generate-with-citations** — LLM if `OPENAI_API_KEY` set; else extractive citation-only labeled `DEGRADED / no-LLM`. No invented sources.
6. **refuse** — `no_hits` (no BM25 matches) / `unauthorized` (matches exist but all ACL-dropped) / `weak_evidence` (authorized but below score threshold).

## Frontmatter / ACL metadata schema (document-level)

See README table. Normalized fields used downstream:

- `allowed_roles: list[str]` — merged from `allowed_roles`, `acl_groups`, and list-form `acl`
- `acl` — original `acl` field if present, else `{"allowed_roles": [...]}`
- `visibility`, `label`, `doc_id`, `title`, `source_path`, `body`

Chunk records inherit `allowed_roles` / `visibility` / `label`. ACL check: non-empty intersection of caller role(s) and chunk `allowed_roles` (case-insensitive). Empty allow-list or missing caller role → deny.

## Data flow

| Stage | Input | Output | Storage |
|-------|-------|--------|---------|
| ingest | files under data dir | doc records + metadata | ephemeral → chunks |
| chunk | doc text | chunk records + doc_id | ephemeral → index |
| index BM25 | chunks | `bm25_meta.json` + `bm25_tokens.pkl` | `indexes/bm25/` |
| index vector | chunks | stub meta only | `indexes/vector/` (`not_real_embeddings`) |
| retrieve | query + caller role | ranked **allowed** chunks | in-memory; ACL at retrieve |
| generate / refuse | query + chunks | answer+citations or refusal | stdout / JSON |

## Distinction from DataPilot

| | DocPilot | DataPilot |
|--|----------|-----------|
| Goal | Document Q&A + citations | NL→SQL / warehouse answers |
| Sources | Docs, FAQs, policies | Tables, SQL dialect |
| Core risk | Leak via retrieval / hallucination | Unsafe SQL / wrong metrics |
| This repo | Yes | No |

## Milestone boundary

- **A:** skeleton, README, stubs, fixture, env example.
- **B:** real MD ingest/chunk/BM25; vector stub; BM25 smoke query CLI.
- **C (this):** ACL-at-retrieve, generate-with-citations, refuse (3 paths), `ask --role`, degraded no-LLM.
- **D+:** not started (real embeddings, PDF, richer eval, etc.).
