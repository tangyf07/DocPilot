# DocPilot architecture

Status: **Milestone A design notes**. Implementation is stubbed; this document describes the intended V1 flow.

## Pipeline

```
┌─────────┐   ┌─────────┐   ┌──────────────────────┐
│ ingest  │ → │ chunk   │ → │ index_bm25           │
└─────────┘   └─────────┘   │ index_vector         │
                            └──────────┬───────────┘
                                       ↓
                            ┌──────────────────────┐
                            │ retrieve (+ ACL)     │
                            └──────────┬───────────┘
                         enough evidence│
                         & authorized?  ├─ no → refuse
                                       ↓ yes
                            ┌──────────────────────┐
                            │ generate + citations │
                            └──────────────────────┘
```

## Stages

1. **ingest** — Load source documents (paths, metadata, ACL labels). Persist raw + normalized text.
2. **chunk** — Split into retrieval units with stable IDs and source offsets for citations.
3. **index (BM25 + vector)** — Lexical index for keyword match; embedding index for semantic match. Hybrid fusion at query time (details TBD in later milestones).
4. **retrieve (ACL)** — Candidate chunks from both indexes, then **filter by caller ACL** before ranking/cutoff. Never return chunks the user cannot read.
5. **generate-with-citations** — LLM answer grounded only on allowed chunks; each claim cites chunk/doc IDs (and preferably spans).
6. **refuse** — If no authorized evidence, confidence below threshold, or policy blocks: return a clear refusal (no invented answer).

## ACL model (V1 intent)

- Documents (and optionally chunks) carry **ACL metadata**, e.g. `acl_groups: ["eng", "hr"]` or `visibility: private|team|public`.
- Request context supplies the **caller identity** and **group memberships**.
- Retrieval applies: `chunk.acl ∩ caller.grants ≠ ∅` (or equivalent allow-list rule).
- Generation never sees filtered-out chunks.
- Refuse path covers both "no match" and "match exists but unauthorized."

Exact schema and enforcement live in `acl.py` (stub in Milestone A).

## Data flow

| Stage | Input | Output | Storage |
|-------|-------|--------|---------|
| ingest | files under `DOCPILOT_DATA_DIR` | doc records + metadata | local FS / later DB |
| chunk | doc text | chunk records + doc_id | local FS |
| index | chunks | BM25 + vector artifacts | `indexes/` (not committed) |
| retrieve | query + caller ACL | ranked allowed chunks | ephemeral |
| generate | query + chunks | answer + citations | response only |
| refuse | reason code | refusal message | response only |

## Distinction from DataPilot

| | DocPilot | DataPilot |
|--|----------|-----------|
| Goal | Document Q&A + citations | NL→SQL / warehouse answers |
| Sources | Docs, FAQs, policies | Tables, SQL dialect |
| Core risk | Leak via retrieval / hallucination | Unsafe SQL / wrong metrics |
| This repo | Yes | No |

## Milestone boundary

- **A (this commit):** skeleton, README, this doc, stubs, fixture, env example.
- **B–E:** real ingest/chunk/index/retrieve/generate/refuse — not started here.