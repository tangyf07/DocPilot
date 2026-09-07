"""Answer generation with citations.

TODO (later milestones): call OpenAI-compatible API with allowed chunks only;
require citations; never invent sources. Milestone A: stub only.
"""

from __future__ import annotations

from typing import Any


def generate_answer(query: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate an answer grounded in chunks, with citations.

    STUB: not implemented. Must not fabricate metrics or sources.
    """
    raise NotImplementedError("TODO: implement generate-with-citations (Milestone B+)")