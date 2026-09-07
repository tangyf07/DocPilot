"""Hybrid retrieval with ACL filtering.

TODO (later milestones): fuse BM25 + vector candidates, apply acl.filter_chunks,
return ranked allowed evidence. Milestone A: stub only.
"""

from __future__ import annotations

from typing import Any


def retrieve(
    query: str,
    *,
    caller: dict[str, Any],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve ACL-allowed chunks for a query.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement hybrid retrieve + ACL (Milestone B+)")