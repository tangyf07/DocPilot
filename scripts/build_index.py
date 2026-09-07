#!/usr/bin/env python3
"""Build BM25 index from sample fixtures and print honest doc/chunk counts.

Usage (from repo root, after pip install -e .):
  python scripts/build_index.py
  python scripts/build_index.py --data-dir data/sample_docs --index-dir indexes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running without install when src/ is present
_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from docpilot.chunking import chunk_documents
from docpilot.index_bm25 import build_bm25_index
from docpilot.index_vector import NOT_REAL_EMBEDDINGS, build_vector_index
from docpilot.ingest import ingest_directory, list_skipped_pdfs


def main() -> int:
    p = argparse.ArgumentParser(description="DocPilot Milestone B: build BM25 from fixtures")
    p.add_argument("--data-dir", type=Path, default=_REPO / "data" / "sample_docs")
    p.add_argument("--index-dir", type=Path, default=_REPO / "indexes")
    p.add_argument("--query", type=str, default="ACL refuse unauthorized", help="optional BM25 smoke query")
    args = p.parse_args()

    if not args.data_dir.is_dir():
        print(f"ERROR: data dir not found: {args.data_dir}", file=sys.stderr)
        return 1

    docs = ingest_directory(args.data_dir)
    chunks = chunk_documents(docs)
    skipped = list_skipped_pdfs(args.data_dir)
    bm25_dir = args.index_dir / "bm25"
    index = build_bm25_index(chunks, bm25_dir)
    vstat = build_vector_index(chunks, args.index_dir / "vector")

    print(f"docs={len(docs)}")
    print(f"chunks={len(chunks)}")
    print(f"bm25_persisted={bm25_dir}")
    print(f"bm25_size={index.size}")
    print(f"vector_stub {NOT_REAL_EMBEDDINGS}={vstat.get(NOT_REAL_EMBEDDINGS)} path={vstat.get('path')}")
    if skipped:
        print(f"skipped_pdfs={skipped} (PDF not implemented)")

    for d in docs:
        print(f"  doc_id={d['doc_id']} path={d['source_path']} roles={d['allowed_roles']} label={d.get('label')}")

    if args.query:
        hits = index.search(args.query, top_k=5)
        print(f"smoke_query={args.query!r} hits={len(hits)}")
        for h in hits:
            print(
                f"  rank={h['rank']} score={h['score']:.4f} "
                f"chunk_id={h['chunk_id']} path={h['source_path']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
