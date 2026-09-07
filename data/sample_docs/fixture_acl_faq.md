---
title: ACL FAQ (FIXTURE)
doc_id: fixture-acl-faq
acl_groups: ["eng", "docs"]
visibility: team
label: FIXTURE
note: Synthetic sample for DocPilot Milestone A. Not production policy. Not real company data.
---

# FIXTURE — Access control FAQ (sample only)

> **FIXTURE DOCUMENT** — For local DocPilot development and eval scaffolding only.
> Do not treat as authoritative policy.

## What is an ACL in DocPilot?

In DocPilot V1, each document (and later each chunk) may carry ACL metadata such as
group allow-lists. Retrieval must drop any chunk the caller is not allowed to read
**before** generation.

## Example groups (fictional)

- `eng` — engineering readers
- `hr` — HR readers
- `docs` — documentation maintainers

## Refuse behavior (intended)

If the only matching chunks are outside the caller's grants, DocPilot should **refuse**
rather than answer from unauthorized text or invent content.

## Citation reminder

Answers must cite the fixture/chunk IDs they used. This file has no live metrics.