"""Document ingest for DocPilot Milestone B.

Supports Markdown with optional YAML frontmatter. PDF is an explicit boundary
stub (not implemented).

Frontmatter / metadata schema (document-level)
---------------------------------------------
Recognized keys (all optional except that body comes from the file):

- ``title`` (str): display title; falls back to first H1 or stem of filename.
- ``doc_id`` (str): stable document id; default ``slug(path.stem)``.
- ``allowed_roles`` (list[str]): role allow-list for later ACL retrieve.
- ``acl_groups`` (list[str]): synonym of ``allowed_roles`` (both merged).
- ``acl`` (list[str] | dict): if list, treated as roles; if dict, kept as-is
  under ``acl`` and any ``roles``/``groups`` keys are merged into roles.
- ``visibility`` (str): e.g. ``private`` | ``team`` | ``public``.
- ``label`` (str): mark fixtures with ``FIXTURE``.
- Other frontmatter keys are preserved under ``extra``.

Normalized doc record fields
----------------------------
``doc_id``, ``title``, ``body``, ``source_path``, ``format`` (``md``),
``allowed_roles``, ``acl``, ``visibility``, ``label``, ``extra``,
``char_count``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SUPPORTED_MD_SUFFIXES = {".md", ".markdown"}
PDF_SUFFIXES = {".pdf"}


class PdfIngestNotImplemented(NotImplementedError):
    """Honest boundary: PDF ingest is not implemented in Milestone B."""


def _slug(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "doc"


def _parse_simple_yaml_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Minimal YAML frontmatter parser (no PyYAML dependency).

    Supports flat scalars, quoted strings, and simple ``[a, b]`` lists.
    Falls back to empty meta + full text if frontmatter is absent/malformed.
    """
    if not raw.startswith("---"):
        return {}, raw
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, raw
    meta_lines = lines[1:end]
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    meta: dict[str, Any] = {}
    for line in meta_lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        meta[key] = _parse_yaml_scalar(val)
    return meta, body


def _parse_yaml_scalar(val: str) -> Any:
    if val == "":
        return ""
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        items = []
        for part in inner.split(","):
            part = part.strip()
            if (part.startswith('"') and part.endswith('"')) or (
                part.startswith("'") and part.endswith("'")
            ):
                items.append(part[1:-1])
            else:
                items.append(part)
        return items
    low = val.lower()
    if low in {"true", "false"}:
        return low == "true"
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    return val


def _first_h1(body: str) -> str | None:
    for line in body.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def _normalize_acl(meta: dict[str, Any]) -> tuple[list[str], Any]:
    roles: list[str] = []
    for key in ("allowed_roles", "acl_groups"):
        val = meta.get(key)
        if isinstance(val, list):
            roles.extend(str(x) for x in val)
        elif isinstance(val, str) and val:
            roles.append(val)
    acl_field: Any = meta.get("acl")
    if isinstance(acl_field, list):
        roles.extend(str(x) for x in acl_field)
    elif isinstance(acl_field, dict):
        for k in ("roles", "groups", "allowed_roles", "acl_groups"):
            v = acl_field.get(k)
            if isinstance(v, list):
                roles.extend(str(x) for x in v)
    # de-dupe preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for r in roles:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq, acl_field


KNOWN_META = {
    "title",
    "doc_id",
    "allowed_roles",
    "acl_groups",
    "acl",
    "visibility",
    "label",
    "note",
}


def ingest_markdown(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    """Load one Markdown file into a normalized doc record."""
    path = path.resolve()
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_simple_yaml_frontmatter(text)
    allowed_roles, acl_field = _normalize_acl(meta)
    title = meta.get("title") or _first_h1(body) or path.stem
    doc_id = str(meta.get("doc_id") or _slug(path.stem))
    rel = str(path.relative_to(root.resolve())) if root else str(path)
    extra = {k: v for k, v in meta.items() if k not in KNOWN_META}
    if "note" in meta:
        extra["note"] = meta["note"]
    return {
        "doc_id": doc_id,
        "title": str(title),
        "body": body,
        "source_path": rel.replace("\\", "/"),
        "format": "md",
        "allowed_roles": allowed_roles,
        "acl": acl_field if acl_field is not None else {"allowed_roles": allowed_roles},
        "visibility": meta.get("visibility"),
        "label": meta.get("label"),
        "extra": extra,
        "char_count": len(body),
    }


def ingest_path(path: Path, *, acl: dict[str, Any] | None = None, root: Path | None = None) -> dict[str, Any]:
    """Ingest a single path into a doc record.

    Markdown is supported. PDF raises ``PdfIngestNotImplemented`` (boundary).
    Optional ``acl`` overlay merges into ``allowed_roles`` after frontmatter.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        raise PdfIngestNotImplemented(
            f"PDF ingest is not implemented (boundary stub): {path}"
        )
    if suffix not in SUPPORTED_MD_SUFFIXES:
        raise ValueError(f"Unsupported ingest format '{suffix}' for {path}")
    doc = ingest_markdown(path, root=root)
    if acl:
        overlay_roles, overlay_acl = _normalize_acl(acl)
        merged = list(doc["allowed_roles"])
        for r in overlay_roles:
            if r not in merged:
                merged.append(r)
        doc["allowed_roles"] = merged
        if overlay_acl is not None:
            doc["acl"] = overlay_acl
    return doc


def ingest_directory(root: Path) -> list[dict[str, Any]]:
    """Ingest all supported Markdown documents under root (recursive).

    PDF files are skipped with a note in the returned list's sidecar via
    ``skipped_pdfs`` attribute is not used; callers can inspect separately.
    Only successfully ingested MD docs are returned.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"Ingest root not found: {root}")
    docs: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in PDF_SUFFIXES:
            # Honest skip — PDF boundary, not silent success.
            continue
        if suffix in SUPPORTED_MD_SUFFIXES:
            docs.append(ingest_markdown(path, root=root))
    return docs


def list_skipped_pdfs(root: Path) -> list[str]:
    """Return relative paths of PDFs under root (not ingested; boundary)."""
    root = Path(root)
    out: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in PDF_SUFFIXES:
            out.append(str(path.relative_to(root)).replace("\\", "/"))
    return out
