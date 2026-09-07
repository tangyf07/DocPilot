---
title: Public Product README (FIXTURE)
doc_id: fixture-public-readme
allowed_roles: ["public"]
visibility: public
label: FIXTURE
note: Synthetic public-facing fixture for DocPilot. Not a real product README.
---

# FIXTURE — Product README (sample only)

> **FIXTURE DOCUMENT** — Labeled fixture for ingest tests.

## What DocPilot is

DocPilot answers questions over documents with citations and access control.
It is not DataPilot (NL→SQL).

## Indexing

Milestone B builds a real BM25 index from Markdown fixtures under `data/sample_docs/`.
PDF ingest remains unimplemented (boundary stub).

## Smoke query ideas

Useful lexical queries against fixtures: `ACL`, `refuse`, `onboarding`, `BM25`, `citations`.
