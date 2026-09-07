"""Access-control helpers for retrieval (Milestone C).

ACL is enforced at retrieve time via ``filter_chunks`` / ``caller_may_read``.
Role matching is case-insensitive against chunk ``allowed_roles``.
"""

from __future__ import annotations

from typing import Any


def _caller_roles(caller: dict[str, Any]) -> list[str]:
    """Normalize caller roles from ``role`` (str) and/or ``roles`` (list)."""
    roles: list[str] = []
    if caller.get("role"):
        roles.append(str(caller["role"]))
    raw = caller.get("roles")
    if isinstance(raw, str) and raw:
        roles.append(raw)
    elif isinstance(raw, (list, tuple)):
        roles.extend(str(x) for x in raw if x)
    # de-dupe, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for r in roles:
        key = r.lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def caller_may_read(caller: dict[str, Any], resource: dict[str, Any]) -> bool:
    """Return True if caller is allowed to read resource (chunk or doc).

    Rules (strict allow-list):
    - Caller must present at least one role.
    - Resource ``allowed_roles`` must be non-empty.
    - Intersection of caller roles and ``allowed_roles`` (case-insensitive)
      must be non-empty.
    - ``visibility`` alone does not bypass the allow-list (public docs use
      ``allowed_roles: ["public"]``).
    """
    roles = _caller_roles(caller)
    if not roles:
        return False
    allowed = [str(x) for x in (resource.get("allowed_roles") or []) if x]
    if not allowed:
        return False
    caller_set = {r.lower() for r in roles}
    allowed_set = {a.lower() for a in allowed}
    return bool(caller_set & allowed_set)


def filter_chunks(caller: dict[str, Any], chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only chunks the caller may read (ACL-at-retrieve)."""
    return [c for c in chunks if caller_may_read(caller, c)]
