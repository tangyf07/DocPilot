"""Hybrid retrieval with ACL filtering at retrieve time (Milestone C).

Pipeline: BM25 candidates -> ACL filter -> score threshold split.
Generation never sees unauthorized chunks. Vector remains stub-only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docpilot.acl import filter_chunks
from docpilot.index_bm25 import BM25Index, load_bm25_index


DEFAULT_REFUSE_THRESHOLD = 0.35


@dataclass
class RetrieveResult:
    """ACL-aware retrieval outcome (filter applied before return)."""

    hits: list[dict[str, Any]]
    """Authorized chunks with score >= min_score (for generation)."""

    allowed_all: list[dict[str, Any]] = field(default_factory=list)
    """All ACL-allowed candidates (including below min_score)."""

    raw_count: int = 0
    """BM25 positive-score hits before ACL."""

    acl_dropped: int = 0
    """Candidates removed by ACL at retrieve time."""

    query: str = ""
    min_score: float = DEFAULT_REFUSE_THRESHOLD
    acl_filtered_at: str = "retrieve"
    backend: str = "bm25"

    @property
    def has_authorized(self) -> bool:
        return bool(self.allowed_all)

    @property
    def has_strong(self) -> bool:
        return bool(self.hits)


def _resolve_bm25_dir(index_dir: Path) -> Path:
    root = Path(index_dir)
    if (root / "bm25").is_dir() and (root / "bm25" / "bm25_meta.json").is_file():
        return root / "bm25"
    return root


def retrieve(
    query: str,
    *,
    caller: dict[str, Any],
    index_dir: Path | str | None = None,
    index: BM25Index | None = None,
    top_k: int = 5,
    candidate_pool: int = 50,
    min_score: float | None = None,
) -> RetrieveResult:
    """Retrieve ACL-allowed chunks for a query.

    ACL filtering happens here (at retrieve), not after generation.
    """
    if min_score is None:
        min_score = float(os.environ.get("DOCPILOT_REFUSE_THRESHOLD", DEFAULT_REFUSE_THRESHOLD))

    if index is None:
        if index_dir is None:
            index_dir = os.environ.get("DOCPILOT_INDEX_DIR") or "indexes"
        index = load_bm25_index(_resolve_bm25_dir(Path(index_dir)))

    raw = index.search(query, top_k=max(candidate_pool, top_k))
    allowed = filter_chunks(caller, raw)
    strong = [c for c in allowed if float(c.get("score") or 0) >= float(min_score)]
    # re-rank positions among returned hits
    hits: list[dict[str, Any]] = []
    for i, c in enumerate(strong[: max(0, top_k)]):
        row = dict(c)
        row["rank"] = i + 1
        hits.append(row)

    return RetrieveResult(
        hits=hits,
        allowed_all=allowed,
        raw_count=len(raw),
        acl_dropped=len(raw) - len(allowed),
        query=query,
        min_score=float(min_score),
        acl_filtered_at="retrieve",
        backend="bm25",
    )
