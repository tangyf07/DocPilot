"""Answer generation with citations (Milestone C).

- With OPENAI_API_KEY: OpenAI-compatible chat completion grounded in chunks.
- Without key: degraded extractive / citation-only mode (clearly labeled).
Never invent sources; every claim cites chunk_id / source_path.
"""

from __future__ import annotations

import os
import re
from typing import Any


DEGRADED_LABEL = "DEGRADED / no-LLM"


def _citation_from_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    text = (chunk.get("text") or "").strip()
    quote = text if len(text) <= 240 else text[:237] + "..."
    return {
        "chunk_id": chunk.get("chunk_id"),
        "doc_id": chunk.get("doc_id"),
        "source_path": chunk.get("source_path"),
        "section_heading": chunk.get("section_heading"),
        "score": chunk.get("score"),
        "quote": quote,
    }


def _format_evidence_block(chunks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for i, c in enumerate(chunks, 1):
        cid = c.get("chunk_id")
        path = c.get("source_path")
        heading = c.get("section_heading") or ""
        text = (c.get("text") or "").strip()
        parts.append(
            f"[{i}] chunk_id={cid} source={path} section={heading!r}\n{text}"
        )
    return "\n\n".join(parts)


def generate_extractive(query: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Citation-only extractive answer (no LLM). Labeled degraded."""
    if not chunks:
        return {
            "status": "error",
            "mode": "degraded_extractive",
            "degraded": True,
            "label": DEGRADED_LABEL,
            "answer": None,
            "citations": [],
            "message": "No chunks provided; cannot extract an answer.",
        }

    citations = [_citation_from_chunk(c) for c in chunks]
    lines = [
        f"[{DEGRADED_LABEL}] Extractive answer from retrieved chunks only "
        "(no OPENAI_API_KEY / no LLM generation).",
        f"Question: {query}",
        "",
        "Evidence excerpts:",
    ]
    for i, cit in enumerate(citations, 1):
        lines.append(
            f"  ({i}) [{cit['chunk_id']}] {cit.get('source_path')} "
            f"- {cit.get('quote')}"
        )
    lines.append("")
    lines.append(
        "Summary: See cited excerpts above. No additional claims were invented."
    )
    return {
        "status": "ok",
        "mode": "degraded_extractive",
        "degraded": True,
        "label": DEGRADED_LABEL,
        "answer": "\n".join(lines),
        "citations": citations,
        "message": DEGRADED_LABEL,
    }


def _openai_available() -> bool:
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    return bool(key)


def generate_llm(query: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """LLM answer grounded in chunks; requires OPENAI_API_KEY."""
    from openai import OpenAI

    citations = [_citation_from_chunk(c) for c in chunks]
    evidence = _format_evidence_block(chunks)
    model = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    client_kwargs: dict[str, Any] = {}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    system = (
        "You are DocPilot, an ACL-aware document QA assistant. "
        "Answer ONLY using the provided evidence chunks. "
        "Every factual claim must cite chunk_id in the form [chunk_id]. "
        "If evidence is insufficient, say you cannot answer from the evidence. "
        "Do not invent sources, metrics, or facts not present in the chunks."
    )
    user = (
        f"Question: {query}\n\n"
        f"Evidence chunks:\n{evidence}\n\n"
        "Write a concise answer with [chunk_id] citations."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    answer = (resp.choices[0].message.content or "").strip()
    # Ensure at least the provided chunk ids are listed as citations even if
    # the model paraphrases; do not invent extra ids.
    cited_ids = set(re.findall(r"\[([^\]]+::chunk-\d+)\]", answer))
    for c in chunks:
        cid = c.get("chunk_id")
        if cid and cid not in cited_ids and cid in answer:
            cited_ids.add(cid)
    # Keep citation list = evidence used (all passed chunks); model must not
    # invent beyond these.
    return {
        "status": "ok",
        "mode": "llm",
        "degraded": False,
        "label": None,
        "answer": answer,
        "citations": citations,
        "model": model,
        "cited_chunk_ids_in_text": sorted(cited_ids),
        "message": "llm",
    }


def generate_answer(query: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate an answer grounded in chunks, with citations.

    Uses LLM when OPENAI_API_KEY is set; otherwise degraded extractive mode.
    Empty chunks -> no invented answer (caller should refuse upstream).
    """
    if not chunks:
        return {
            "status": "error",
            "mode": "none",
            "degraded": not _openai_available(),
            "answer": None,
            "citations": [],
            "message": "No evidence chunks; refusing to invent an answer.",
        }
    if _openai_available():
        try:
            return generate_llm(query, chunks)
        except Exception as exc:  # noqa: BLE001 - fall back, label clearly
            fallback = generate_extractive(query, chunks)
            fallback["message"] = (
                f"{DEGRADED_LABEL} (LLM call failed: {type(exc).__name__}: {exc})"
            )
            fallback["llm_error"] = f"{type(exc).__name__}: {exc}"
            return fallback
    return generate_extractive(query, chunks)
