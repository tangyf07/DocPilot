#!/usr/bin/env python3
"""Demo Milestone C ask paths (authorized / refuse x3 / degraded).

Usage (from repo root):
  python scripts/demo_ask_c.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Ensure no key for degraded demo unless user exported one
# (script still works with key; labels mode accordingly)

from docpilot.generate import generate_answer
from docpilot.refuse import refuse_from_retrieve
from docpilot.retrieve import retrieve


def _run(title: str, question: str, role: str, **kwargs) -> None:
    print("=" * 60)
    print(title)
    print(f"role={role!r} question={question!r}")
    res = retrieve(question, caller={"role": role}, index_dir=_REPO / "indexes", **kwargs)
    print(
        f"retrieve: raw={res.raw_count} acl_dropped={res.acl_dropped} "
        f"allowed={len(res.allowed_all)} strong={len(res.hits)} "
        f"acl_filtered_at={res.acl_filtered_at}"
    )
    refused = refuse_from_retrieve(res)
    if refused:
        print(f"OUTCOME: refuse/{refused['reason']}")
        print(refused["message"])
        return
    gen = generate_answer(question, res.hits)
    print(f"OUTCOME: answer mode={gen.get('mode')} degraded={gen.get('degraded')}")
    if gen.get("label"):
        print(f"label={gen['label']}")
    print((gen.get("answer") or "")[:500])
    print("citations:", [c.get("chunk_id") for c in gen.get("citations") or []])


def main() -> int:
    idx = _REPO / "indexes" / "bm25"
    if not (idx / "bm25_meta.json").is_file():
        print("ERROR: indexes missing; run: python scripts/build_index.py", file=sys.stderr)
        return 1
    os.environ.pop("OPENAI_API_KEY", None)  # force degraded path for demo clarity
    _run(
        "(a) authorized ask with citations (degraded / no-LLM)",
        "What is ACL refuse behavior?",
        "eng",
        min_score=0.01,
    )
    _run(
        "(b) unauthorized refuse (ACL at retrieve)",
        "ACL refuse unauthorized",
        "contractor",
        min_score=0.01,
    )
    _run(
        "(c) no-hit refuse",
        "xyzzyqwertynonexistent999zzz",
        "eng",
        min_score=0.01,
    )
    _run(
        "(d) weak-evidence refuse",
        "ACL refuse",
        "eng",
        min_score=1000.0,
    )
    print("=" * 60)
    print("(e) no-key degraded mode: OPENAI_API_KEY unset above; see (a) label.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
