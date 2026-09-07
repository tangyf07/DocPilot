#!/usr/bin/env python3
"""DocPilot V1 interview one-shot demo (Milestone E).

Runs end-to-end on fixtures:
  1) ingest / build BM25 (+ vector stub marker)
  2) authorized ask with citations
  3) three refuse paths (unauthorized / no_hits / weak_evidence)
  4) offline GOLD eval summary (DEGRADED / no-LLM)

Default forces DEGRADED / no-LLM (clears OPENAI_API_KEY) so screen-share
output is deterministic and does not require an API key.

Usage (from repo root, with .venv activated or via .venv\Scripts\python):
  python scripts/demo_v1.py
  python scripts/demo_v1.py --skip-build          # reuse existing indexes/
  python scripts/demo_v1.py --eval-limit 12       # shorter eval for time
  python scripts/demo_v1.py --keep-api-key        # allow live LLM if key set

Honesty:
  - Vector index remains not_real_embeddings (stub). Retrieval path is BM25+ACL.
  - Eval metrics are computed from this run only — not hardcoded accuracy.
  - Without an API key (default), answers are labeled DEGRADED / no-LLM.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from docpilot.chunking import chunk_documents
from docpilot.eval_runner import format_report, run_eval
from docpilot.generate import generate_answer
from docpilot.index_bm25 import build_bm25_index
from docpilot.index_vector import NOT_REAL_EMBEDDINGS, build_vector_index
from docpilot.ingest import ingest_directory, list_skipped_pdfs
from docpilot.refuse import refuse_from_retrieve
from docpilot.retrieve import retrieve


def _banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _hr() -> None:
    print("-" * 72)


def build_indexes(*, data_dir: Path, index_dir: Path) -> dict:
    docs = ingest_directory(data_dir)
    chunks = chunk_documents(docs)
    skipped = list_skipped_pdfs(data_dir)
    bm25 = build_bm25_index(chunks, index_dir / "bm25")
    vstat = build_vector_index(chunks, index_dir / "vector")
    return {
        "docs": len(docs),
        "chunks": len(chunks),
        "bm25_size": bm25.size,
        "skipped_pdfs": skipped,
        "vector_stub": bool(vstat.get(NOT_REAL_EMBEDDINGS)),
        "vector_path": vstat.get("path"),
        "doc_rows": [
            {
                "doc_id": d["doc_id"],
                "path": d["source_path"],
                "roles": d["allowed_roles"],
                "label": d.get("label"),
            }
            for d in docs
        ],
    }


def run_ask(
    title: str,
    question: str,
    role: str,
    *,
    index_dir: Path,
    min_score: float = 0.01,
) -> str:
    """Run one ask path; return outcome tag (answer / refuse/<reason>)."""
    _banner(title)
    print(f"role={role!r}")
    print(f"question={question!r}")
    _hr()
    res = retrieve(
        question,
        caller={"role": role},
        index_dir=index_dir,
        min_score=min_score,
    )
    print(
        f"retrieve: backend={res.backend} raw={res.raw_count} "
        f"acl_dropped={res.acl_dropped} allowed={len(res.allowed_all)} "
        f"strong={len(res.hits)} acl_filtered_at={res.acl_filtered_at} "
        f"min_score={res.min_score}"
    )
    refused = refuse_from_retrieve(res)
    if refused:
        reason = refused.get("reason")
        print(f"OUTCOME: refuse / {reason}")
        print(refused.get("message") or "")
        return f"refuse/{reason}"

    gen = generate_answer(question, res.hits)
    print(
        f"OUTCOME: answer  mode={gen.get('mode')}  "
        f"degraded={gen.get('degraded')}  label={gen.get('label')}"
    )
    answer = (gen.get("answer") or "").strip()
    # Keep screen-share readable
    if len(answer) > 900:
        print(answer[:900] + "\n... [truncated for demo] ...")
    else:
        print(answer)
    cites = [c.get("chunk_id") for c in (gen.get("citations") or [])]
    print(f"citations(chunk_id)={cites}")
    return "answer"


def main() -> int:
    p = argparse.ArgumentParser(
        description="DocPilot V1 interview one-shot demo (Milestone E)"
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=_REPO / "data" / "sample_docs",
        help="Fixture docs root",
    )
    p.add_argument(
        "--index-dir",
        type=Path,
        default=_REPO / "indexes",
        help="Index output / load dir",
    )
    p.add_argument(
        "--gold",
        type=Path,
        default=_REPO / "data" / "eval" / "gold_milestone_d.jsonl",
        help="GOLD JSONL for eval summary",
    )
    p.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip ingest/build; require existing BM25 under --index-dir",
    )
    p.add_argument(
        "--eval-limit",
        type=int,
        default=None,
        help="Optional max GOLD items (default: full set)",
    )
    p.add_argument(
        "--keep-api-key",
        action="store_true",
        help=(
            "Do not clear OPENAI_API_KEY. Ask may use live LLM if a key is set. "
            "Eval summary still defaults to DEGRADED / no-LLM unless you also "
            "pass --live-eval."
        ),
    )
    p.add_argument(
        "--live-eval",
        action="store_true",
        help=(
            "Optional experimental live-LLM eval (labeled not_real_api). "
            "Default eval path remains DEGRADED / no-LLM."
        ),
    )
    args = p.parse_args()

    t0 = time.perf_counter()

    _banner("DocPilot V1 — interview one-shot demo (Milestone E)")
    print("NOT DataPilot (NL->SQL). This is document RAG + ACL + citations.")
    print(f"repo={_REPO}")
    print(f"data_dir={args.data_dir}")
    print(f"index_dir={args.index_dir}")
    print(f"gold={args.gold}")

    if not args.keep_api_key:
        os.environ.pop("OPENAI_API_KEY", None)
        print("mode=DEGRADED / no-LLM  (OPENAI_API_KEY cleared for demo clarity)")
    else:
        has_key = bool(os.environ.get("OPENAI_API_KEY"))
        print(
            f"mode=keep-api-key  OPENAI_API_KEY_set={has_key}  "
            "(live generation only if key present)"
        )

    # --- 1) ingest / build ---
    if args.skip_build:
        meta = args.index_dir / "bm25" / "bm25_meta.json"
        if not meta.is_file() and not (args.index_dir / "bm25_meta.json").is_file():
            print(
                f"ERROR: BM25 index missing under {args.index_dir}; "
                "run without --skip-build or: python scripts/build_index.py",
                file=sys.stderr,
            )
            return 1
        _banner("STEP 1/4 — ingest/build (skipped; reusing indexes)")
        print(f"bm25_meta present under {args.index_dir}")
        print(
            "NOTE: vector artifact (if present) is still a stub "
            f"({NOT_REAL_EMBEDDINGS}=True). Real retrieval = BM25 + ACL."
        )
    else:
        if not args.data_dir.is_dir():
            print(f"ERROR: data dir not found: {args.data_dir}", file=sys.stderr)
            return 1
        _banner("STEP 1/4 — ingest Markdown fixtures -> chunk -> BM25 (+ vector stub)")
        stats = build_indexes(data_dir=args.data_dir, index_dir=args.index_dir)
        print(f"docs={stats['docs']}  chunks={stats['chunks']}  bm25_size={stats['bm25_size']}")
        print(
            f"vector_stub {NOT_REAL_EMBEDDINGS}={stats['vector_stub']}  "
            f"path={stats['vector_path']}"
        )
        print(
            "NOTE: vector is NOT real embeddings. Hybrid vector retrieval is not "
            "a V1 selling point — BM25 + ACL-at-retrieve is the real path."
        )
        if stats["skipped_pdfs"]:
            print(f"skipped_pdfs={stats['skipped_pdfs']} (PDF ingest not implemented)")
        for row in stats["doc_rows"]:
            print(
                f"  doc_id={row['doc_id']} path={row['path']} "
                f"roles={row['roles']} label={row['label']}"
            )

    # --- 2) authorized ask ---
    outcomes: list[tuple[str, str]] = []
    outcomes.append(
        (
            "authorized",
            run_ask(
                "STEP 2/4 — (a) authorized ask -> answer + citations",
                "What is ACL refuse behavior?",
                "eng",
                index_dir=args.index_dir,
                min_score=0.01,
            ),
        )
    )

    # --- 3) three refuse paths ---
    outcomes.append(
        (
            "unauthorized",
            run_ask(
                "STEP 3/4 — (b) refuse / unauthorized (ACL at retrieve)",
                "ACL refuse unauthorized",
                "contractor",
                index_dir=args.index_dir,
                min_score=0.01,
            ),
        )
    )
    outcomes.append(
        (
            "no_hits",
            run_ask(
                "STEP 3/4 — (c) refuse / no_hits",
                "xyzzyqwertynonexistent999zzz",
                "eng",
                index_dir=args.index_dir,
                min_score=0.01,
            ),
        )
    )
    outcomes.append(
        (
            "weak_evidence",
            run_ask(
                "STEP 3/4 — (d) refuse / weak_evidence",
                "ACL refuse",
                "eng",
                index_dir=args.index_dir,
                min_score=1000.0,
            ),
        )
    )

    # --- 4) eval summary ---
    _banner("STEP 4/4 — offline GOLD eval summary (reuse run_eval)")
    if not args.gold.is_file():
        print(f"ERROR: gold file not found: {args.gold}", file=sys.stderr)
        return 1
    force_degraded = not args.live_eval
    if args.live_eval:
        print("eval_mode request=live_experimental / not_real_api  (NOT production API eval)")
    else:
        print("eval_mode request=DEGRADED / no-LLM  (default; no fabricated accuracy)")
    report = run_eval(
        args.gold,
        index_dir=args.index_dir,
        force_degraded=force_degraded,
        limit=args.eval_limit,
    )
    print(format_report(report))
    metrics = report.get("metrics") or {}
    failures = int(metrics.get("failure_count") or 0)

    # --- closing summary ---
    _banner("Demo summary (V1 closed A-E)")
    print("Ask path outcomes:")
    for name, tag in outcomes:
        print(f"  {name}: {tag}")
    print(
        f"Eval: gold_count={report.get('gold_count')}  "
        f"failure_count={failures}  "
        f"eval_mode={(report.get('honesty') or {}).get('eval_mode')}"
    )
    print(
        "Honesty reminders: BM25+ACL real; vector=stub (not_real_embeddings); "
        "eval numbers from this run only; answer_heuristic != accuracy."
    )
    elapsed = time.perf_counter() - t0
    print(f"elapsed_sec={elapsed:.1f}")
    print("Done. Interview command:  python scripts/demo_v1.py")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
