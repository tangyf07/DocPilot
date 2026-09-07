"""Vector / embedding index.

TODO (later milestones): embed chunks, persist vector store, ANN search.
Milestone A: stub only. Do not commit generated indexes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_vector_index(chunks: list[dict[str, Any]], index_dir: Path) -> None:
    """Build and persist a vector index.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement vector index build (Milestone B+)")


def search_vector(query: str, index_dir: Path, *, top_k: int = 5) -> list[dict[str, Any]]:
    """Semantic search over the vector index.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement vector search (Milestone B+)")