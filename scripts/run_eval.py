#!/usr/bin/env python3
"""Run Milestone D offline gold eval (default: DEGRADED / no-LLM).

Usage (from repo root):
  python scripts/run_eval.py
  python scripts/run_eval.py --gold data/eval/gold_milestone_d.jsonl --index-dir indexes
  python scripts/run_eval.py --limit 8
  python scripts/run_eval.py --live-llm   # optional experimental; labeled not_real_api

Metrics are computed from this run only. No hardcoded accuracy numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from docpilot.eval_runner import format_report, run_eval


def main() -> int:
    p = argparse.ArgumentParser(
        description="DocPilot Milestone D offline eval (default DEGRADED / no-LLM)"
    )
    p.add_argument(
        "--gold",
        type=Path,
        default=_REPO / "data" / "eval" / "gold_milestone_d.jsonl",
        help="GOLD JSONL path",
    )
    p.add_argument(
        "--index-dir",
        type=Path,
        default=_REPO / "indexes",
        help="Index dir containing bm25/",
    )
    p.add_argument("--limit", type=int, default=None, help="Optional max gold items")
    p.add_argument(
        "--category",
        action="append",
        default=None,
        help="Filter category (repeatable)",
    )
    p.add_argument(
        "--live-llm",
        action="store_true",
        help=(
            "Optional experimental live LLM if OPENAI_API_KEY is set. "
            "Labeled not_real_api — NOT a production API eval. "
            "Default remains DEGRADED / no-LLM."
        ),
    )
    p.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write full JSON report",
    )
    args = p.parse_args()

    if not args.gold.is_file():
        print(f"ERROR: gold file not found: {args.gold}", file=sys.stderr)
        return 1
    bm25_meta = args.index_dir / "bm25" / "bm25_meta.json"
    if not bm25_meta.is_file() and not (args.index_dir / "bm25_meta.json").is_file():
        print(
            f"ERROR: BM25 index missing under {args.index_dir}; "
            "run: python scripts/build_index.py",
            file=sys.stderr,
        )
        return 1

    force_degraded = not args.live_llm
    report = run_eval(
        args.gold,
        index_dir=args.index_dir,
        force_degraded=force_degraded,
        limit=args.limit,
        categories=args.category,
    )
    print(format_report(report))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\njson_out={args.json_out}")
    metrics = report.get("metrics") or {}
    if int(metrics.get("failure_count") or 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
