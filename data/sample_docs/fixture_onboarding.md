---
title: Onboarding Handbook Excerpt (FIXTURE)
doc_id: fixture-onboarding
allowed_roles: ["eng", "hr"]
visibility: team
label: FIXTURE
note: Synthetic onboarding excerpt for DocPilot ingest/chunk/index smoke tests only.
---

# FIXTURE — Onboarding handbook (sample only)

> **FIXTURE DOCUMENT** — Not real HR policy. For DocPilot Milestone B indexing only.

## Welcome

Welcome to the fictional company. This handbook excerpt exists so the BM25 index
has a second Markdown source with ACL frontmatter (`allowed_roles`).

## Laptop setup

1. Install the approved editor.
2. Clone internal repos you are granted access to.
3. Never commit secrets or `.env` files.

## Who to ask

- Engineering questions → `eng` peers
- Benefits questions → `hr` (this fixture does not contain real benefits data)

## Document Q&A note

DocPilot indexes this file for lexical search smoke tests. Vector embeddings are
not used here; any vector path is a stub marked `not_real_embeddings`.
