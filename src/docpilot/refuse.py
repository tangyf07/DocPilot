"""Explicit refuse path when evidence is missing, weak, or unauthorized."""

from __future__ import annotations

from typing import Any

from docpilot.retrieve import RetrieveResult

REASON_NO_HITS = "no_hits"
REASON_UNAUTHORIZED = "unauthorized"
REASON_WEAK_EVIDENCE = "weak_evidence"

REFUSE_MESSAGES = {
    REASON_NO_HITS: (
        "REFUSE: no indexed evidence matched this query. "
        "DocPilot will not invent an answer."
    ),
    REASON_UNAUTHORIZED: (
        "REFUSE: matching documents exist but none are authorized for your role "
        "(ACL filtered at retrieve). DocPilot will not answer from unauthorized text."
    ),
    REASON_WEAK_EVIDENCE: (
        "REFUSE: authorized hits exist but evidence scores are below the refuse "
        "threshold (weak evidence). DocPilot will not guess."
    ),
}


def classify_retrieve(result: RetrieveResult) -> str | None:
    """Return a refuse reason code, or None if generation may proceed.

    Order:
    1. no BM25 hits at all -> no_hits
    2. BM25 hits but all dropped by ACL -> unauthorized
    3. ACL-allowed hits but none meet min_score -> weak_evidence
    4. otherwise -> None (answer)
    """
    if result.raw_count <= 0:
        return REASON_NO_HITS
    if not result.allowed_all:
        return REASON_UNAUTHORIZED
    if not result.hits:
        return REASON_WEAK_EVIDENCE
    return None


def should_refuse(chunks: list[dict[str, Any]], *, threshold: float) -> bool:
    """Legacy helper: True when there are no chunks at/above threshold."""
    if not chunks:
        return True
    return max(float(c.get("score") or 0) for c in chunks) < float(threshold)


def refuse(reason: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a structured refusal response (no invented answer)."""
    details = dict(details or {})
    message = REFUSE_MESSAGES.get(reason, f"REFUSE: {reason}")
    return {
        "status": "refuse",
        "reason": reason,
        "message": message,
        "answer": None,
        "citations": [],
        "details": details,
    }


def refuse_from_retrieve(result: RetrieveResult) -> dict[str, Any] | None:
    """If retrieve outcome requires refuse, return refuse dict; else None."""
    reason = classify_retrieve(result)
    if reason is None:
        return None
    return refuse(
        reason,
        details={
            "query": result.query,
            "raw_count": result.raw_count,
            "acl_dropped": result.acl_dropped,
            "allowed_count": len(result.allowed_all),
            "strong_count": len(result.hits),
            "min_score": result.min_score,
            "acl_filtered_at": result.acl_filtered_at,
            "backend": result.backend,
        },
    )
