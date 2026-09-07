"""Document ingest.

TODO (later milestones): load files from DOCPILOT_DATA_DIR, extract text,
attach ACL metadata, persist normalized docs. Milestone A: stub only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def ingest_path(path: Path, *, acl: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ingest a single path into a doc record.

    STUB: does not read or index anything yet.
    """
    raise NotImplementedError("TODO: implement ingest (Milestone B+)")


def ingest_directory(root: Path) -> list[dict[str, Any]]:
    """Ingest all supported documents under root.

    STUB: returns nothing useful yet.
    """
    raise NotImplementedError("TODO: implement directory ingest (Milestone B+)")