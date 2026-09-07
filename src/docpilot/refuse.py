"""Explicit refuse path when evidence is weak or unauthorized.

TODO (later milestones): map reason codes to user-facing refusals;
integrate with retrieve confidence / ACL outcomes. Milestone A: stub only.
"""

from __future__ import annotations

from typing import Any


def should_refuse(chunks: list[dict[str, Any]], *, threshold: float) -> bool:
    """Decide whether to refuse instead of generating.

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement refuse decision (Milestone B+)")


def refuse(reason: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a structured refusal response (no invented answer).

    STUB: not implemented.
    """
    raise NotImplementedError("TODO: implement refuse response (Milestone B+)")