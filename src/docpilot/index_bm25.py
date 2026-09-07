"""BM25 lexical index.

TODO (later milestones): build/load BM25 over chunks; query top-k.
Milestone A: stub only. Indexes should live under indexes/ (gitignored).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_bm25_index(chunks: list[dict[str, Any]], index_dir: Path) -> None:
    """Build and persist a BM25 index.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement BM25 index build (Milestone B+)")


def search_bm25(query: str, index_dir: Path, *, top_k: int = 5) -> list[dict[str, Any]]:
    """Search BM25 index.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement BM25 search (Milestone B+)")