"""Text chunking for retrieval units (Milestone B).

Splits Markdown primarily on ATX headings (##+), falling back to paragraph
blocks. Each chunk gets a stable ``chunk_id`` derived from ``doc_id`` + index,
keeps ``source_path``, character offsets into the document body, and the
nearest section heading when available.
"""

from __future__ import annotations

import re
from typing import Any

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _paragraph_spans(body: str) -> list[tuple[int, int, str]]:
    """Return (start, end, text) for non-empty paragraph-like blocks."""
    spans: list[tuple[int, int, str]] = []
    pos = 0
    for part in re.split(r"\n\s*\n", body):
        if not part.strip():
            # advance past delimiter
            idx = body.find(part, pos)
            if idx >= 0:
                pos = idx + len(part)
            continue
        idx = body.find(part, pos)
        if idx < 0:
            idx = pos
        start, end = idx, idx + len(part)
        spans.append((start, end, part.strip()))
        pos = end
    return spans


def _heading_sections(body: str) -> list[dict[str, Any]]:
    """Split body into sections keyed by heading; preamble has heading=None."""
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        return [{"heading": None, "level": 0, "start": 0, "end": len(body), "text": body}]

    sections: list[dict[str, Any]] = []
    # preamble before first heading
    if matches[0].start() > 0:
        pre = body[: matches[0].start()]
        if pre.strip():
            sections.append(
                {
                    "heading": None,
                    "level": 0,
                    "start": 0,
                    "end": matches[0].start(),
                    "text": pre,
                }
            )
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append(
            {
                "heading": m.group(2).strip(),
                "level": len(m.group(1)),
                "start": start,
                "end": end,
                "text": body[start:end],
            }
        )
    return sections


def _split_oversized(text: str, base_start: int, max_chars: int) -> list[tuple[int, int, str]]:
    """Greedy char windows with overlap-free cuts on newlines when possible."""
    text_len = len(text)
    if text_len <= max_chars:
        return [(base_start, base_start + text_len, text.strip())] if text.strip() else []
    out: list[tuple[int, int, str]] = []
    i = 0
    while i < text_len:
        j = min(i + max_chars, text_len)
        if j < text_len:
            cut = text.rfind("\n", i, j)
            if cut > i + max_chars // 4:
                j = cut
        piece = text[i:j]
        if piece.strip():
            out.append((base_start + i, base_start + j, piece.strip()))
        if j == i:
            j = i + 1
        i = j
    return out


def chunk_document(
    doc: dict[str, Any],
    *,
    max_chars: int = 1200,
    max_tokens: int = 512,
) -> list[dict[str, Any]]:
    """Split a document into retrieval chunks with stable IDs.

    ``max_tokens`` is accepted for API compatibility; sizing uses ``max_chars``
    (approx ``max_tokens * 4`` when caller leaves default max_chars).
    """
    if max_chars == 1200 and max_tokens != 512:
        max_chars = max(200, max_tokens * 4)

    body = doc.get("body") or ""
    doc_id = str(doc.get("doc_id") or "doc")
    source_path = doc.get("source_path")
    allowed_roles = list(doc.get("allowed_roles") or [])
    visibility = doc.get("visibility")
    label = doc.get("label")
    title = doc.get("title")

    sections = _heading_sections(body)
    raw_pieces: list[dict[str, Any]] = []
    for sec in sections:
        for start, end, text in _split_oversized(sec["text"], sec["start"], max_chars):
            if not text:
                continue
            raw_pieces.append(
                {
                    "text": text,
                    "char_start": start,
                    "char_end": end,
                    "section_heading": sec["heading"],
                }
            )

    if not raw_pieces and body.strip():
        raw_pieces.append(
            {
                "text": body.strip(),
                "char_start": 0,
                "char_end": len(body),
                "section_heading": None,
            }
        )

    chunks: list[dict[str, Any]] = []
    for i, piece in enumerate(raw_pieces):
        chunk_id = f"{doc_id}::chunk-{i:04d}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "text": piece["text"],
                "source_path": source_path,
                "char_start": piece["char_start"],
                "char_end": piece["char_end"],
                "section_heading": piece["section_heading"],
                "title": title,
                "allowed_roles": allowed_roles,
                "visibility": visibility,
                "label": label,
                "chunk_index": i,
            }
        )
    return chunks


def chunk_documents(docs: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
    """Chunk many docs; concatenate results in input order."""
    out: list[dict[str, Any]] = []
    for doc in docs:
        out.extend(chunk_document(doc, **kwargs))
    return out
