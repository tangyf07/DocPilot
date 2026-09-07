"""Vector / embedding index — STUB (Milestone B).

This module exposes an embed+store interface but does **not** produce real
embeddings or real semantic retrieval quality.

Marker (required): ``not_real_embeddings``
Use this constant / field name in persisted metadata and return payloads so
callers never mistake stub output for production vector search.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Required honesty marker — do not remove or rename without updating README.
not_real_embeddings = True
NOT_REAL_EMBEDDINGS = "not_real_embeddings"

STUB_META_NAME = "vector_stub_meta.json"


class VectorIndexStub:
    """Degradable stub: stores chunk ids only; search returns empty + marker."""

    def __init__(self, chunks: list[dict[str, Any]] | None = None):
        self.chunks = list(chunks or [])
        self.not_real_embeddings = True

    @property
    def size(self) -> int:
        return len(self.chunks)

    def save(self, index_dir: Path) -> Path:
        index_dir = Path(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            NOT_REAL_EMBEDDINGS: True,
            "status": "stub",
            "message": (
                "Vector index is a stub. No embedding model or API key is used. "
                "Do not treat search results as semantic retrieval quality."
            ),
            "chunk_ids": [c.get("chunk_id") for c in self.chunks],
            "chunk_count": len(self.chunks),
        }
        path = index_dir / STUB_META_NAME
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, index_dir: Path) -> "VectorIndexStub":
        index_dir = Path(index_dir)
        path = index_dir / STUB_META_NAME
        if not path.is_file():
            # Degrade gracefully: empty stub
            return cls([])
        meta = json.loads(path.read_text(encoding="utf-8"))
        stub = cls([])
        stub.chunks = [{"chunk_id": cid} for cid in meta.get("chunk_ids") or []]
        stub.not_real_embeddings = bool(meta.get(NOT_REAL_EMBEDDINGS, True))
        return stub

    def search(self, query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        """Always returns empty hits; payload marked ``not_real_embeddings``."""
        _ = (query, top_k)
        return []


def build_vector_index(chunks: list[dict[str, Any]], index_dir: Path) -> dict[str, Any]:
    """STUB build: persist marker metadata only (no embeddings).

    Returns a status dict with ``not_real_embeddings=True``.
    Degrades when no embedding model/key is configured (always, in Milestone B).
    """
    stub = VectorIndexStub(chunks)
    path = stub.save(Path(index_dir))
    return {
        NOT_REAL_EMBEDDINGS: True,
        "status": "stub",
        "path": str(path),
        "chunk_count": stub.size,
        "message": "Vector index stub written; not real embeddings.",
    }


def search_vector(query: str, index_dir: Path, *, top_k: int = 5) -> dict[str, Any]:
    """STUB search: no semantic hits. Marked ``not_real_embeddings``."""
    stub = VectorIndexStub.load(Path(index_dir))
    hits = stub.search(query, top_k=top_k)
    return {
        NOT_REAL_EMBEDDINGS: True,
        "status": "stub",
        "hits": hits,
        "message": "Vector search is a stub; returning no semantic hits.",
    }
