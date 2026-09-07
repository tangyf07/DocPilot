"""Text chunking for retrieval units.

TODO (later milestones): split documents into stable chunks with offsets
for citations. Milestone A: stub only.
"""

from __future__ import annotations

from typing import Any


def chunk_document(doc: dict[str, Any], *, max_tokens: int = 512) -> list[dict[str, Any]]:
    """Split a document into retrieval chunks.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement chunking (Milestone B+)")