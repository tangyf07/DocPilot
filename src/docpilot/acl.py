"""Access-control helpers for retrieval and generation.

TODO (later milestones): define ACL schema on docs/chunks; enforce
caller grants before any chunk reaches the LLM. Milestone A: stub only.
"""

from __future__ import annotations

from typing import Any


def caller_may_read(caller: dict[str, Any], resource: dict[str, Any]) -> bool:
    """Return True if caller is allowed to read resource.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement ACL check (Milestone B+)")


def filter_chunks(caller: dict[str, Any], chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop chunks the caller cannot read.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement ACL filter (Milestone B+)")