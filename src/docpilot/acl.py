"""Access-control helpers for retrieval and generation.

Milestone B: ACL fields are ingested/attached on docs/chunks for later use.
Enforcement at retrieve time is Milestone C — not implemented here.
"""

from __future__ import annotations

from typing import Any


def caller_may_read(caller: dict[str, Any], resource: dict[str, Any]) -> bool:
    """Return True if caller is allowed to read resource.

    STUB: ACL-at-retrieve is Milestone C — not implemented.
    """
    raise NotImplementedError("TODO: implement ACL check (Milestone C)")


def filter_chunks(caller: dict[str, Any], chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop chunks the caller cannot read.

    STUB: ACL-at-retrieve is Milestone C — not implemented.
    """
    raise NotImplementedError("TODO: implement ACL filter (Milestone C)")
