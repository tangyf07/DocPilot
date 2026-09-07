"""Offline eval for Milestone D gold fixtures.

Default path: DEGRADED / no-LLM (forces no OPENAI_API_KEY).
Optional live LLM path is labeled experimental / not_real_api — not production API eval.

Metrics are computed only from the current run (never hardcoded):
- refuse_correctness: expected refuse/ok status (+ reason) vs actual
- citation_coverage: when answer expected, citations must include chunk_id
- answer_heuristic: simple token overlap (labeled heuristic — not accuracy)
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from docpilot.generate import DEGRADED_LABEL, generate_answer
from docpilot.refuse import refuse_from_retrieve
from docpilot.retrieve import retrieve

EVAL_MODE_DEGRADED = "DEGRADED / no-LLM"
EVAL_MODE_LIVE_EXPERIMENTAL = "live_experimental / not_real_api"

# Honesty marker for optional live path (not a validated production API eval).
NOT_REAL_API = "not_real_api"


@dataclass
class GoldItem:
    id: str
    category: str
    query: str
    role: str
    expect_status: str
    expect_reason: str | None
    require_citations: bool
    min_score: float = 0.01
    label: str = "GOLD"
    notes: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseResult:
    id: str
    category: str
    query: str
    role: str
    expect_status: str
    expect_reason: str | None
    actual_status: str
    actual_reason: str | None
    refuse_ok: bool
    citation_ok: bool | None  # None when not applicable
    heuristic_ok: bool | None
    heuristic_score: float | None
    citations: list[str]
    mode: str
    degraded: bool
    details: dict[str, Any] = field(default_factory=dict)


def load_gold(path: Path | str) -> list[GoldItem]:
    """Load GOLD JSONL (one object per line). Lines starting with # ignored."""
    p = Path(path)
    items: list[GoldItem] = []
    with p.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            expect = row.get("expect") or {}
            items.append(
                GoldItem(
                    id=str(row.get("id") or f"line-{line_no}"),
                    category=str(row.get("category") or "unknown"),
                    query=str(row["query"]),
                    role=str(row["role"]),
                    expect_status=str(expect.get("status") or "ok"),
                    expect_reason=expect.get("reason"),
                    require_citations=bool(expect.get("require_citations", False)),
                    min_score=float(row.get("min_score", 0.01)),
                    label=str(row.get("label") or "GOLD"),
                    notes=str(row.get("notes") or ""),
                    raw=row,
                )
            )
    return items


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", (text or "").lower()) if len(t) >= 3}


def answer_heuristic(query: str, answer: str | None, citations: list[dict[str, Any]]) -> tuple[bool, float]:
    """Simple token-overlap heuristic - NOT accuracy).

    Score = |query_tokens ∩ evidence_tokens| / max(1, |query_tokens|).
    Passes if score >= 0.15 or any citation quote overlaps a query token.
    Labeled heuristic only — do not market as accuracy.
    """
    q_toks = _tokenize(query)
    if not q_toks:
        return False, 0.0
    evidence_parts: list[str] = [answer or ""]
    for c in citations or []:
        evidence_parts.append(str(c.get("quote") or ""))
        evidence_parts.append(str(c.get("chunk_id") or ""))
    e_toks = _tokenize(" ".join(evidence_parts))
    inter = q_toks & e_toks
    score = len(inter) / max(1, len(q_toks))
    return score >= 0.15, round(score, 4)


def run_one(
    item: GoldItem,
    *,
    index_dir: Path,
    force_degraded: bool = True,
) -> CaseResult:
    """Run one gold item through retrieve → refuse/generate."""
    if force_degraded:
        os.environ.pop("OPENAI_API_KEY", None)

    res = retrieve(
        item.query,
        caller={"role": item.role},
        index_dir=index_dir,
        top_k=5,
        min_score=item.min_score,
    )
    refused = refuse_from_retrieve(res)
    if refused is not None:
        actual_status = "refuse"
        actual_reason = refused.get("reason")
        citations: list[dict[str, Any]] = []
        answer = None
        mode = "refuse"
        degraded = True
        details = {
            "raw_count": res.raw_count,
            "acl_dropped": res.acl_dropped,
            "allowed_count": len(res.allowed_all),
            "strong_count": len(res.hits),
            "acl_filtered_at": res.acl_filtered_at,
            "message": refused.get("message"),
        }
    else:
        gen = generate_answer(item.query, res.hits)
        actual_status = "ok" if gen.get("status") == "ok" else str(gen.get("status"))
        actual_reason = None
        citations = list(gen.get("citations") or [])
        answer = gen.get("answer")
        mode = str(gen.get("mode") or "unknown")
        degraded = bool(gen.get("degraded"))
        details = {
            "raw_count": res.raw_count,
            "acl_dropped": res.acl_dropped,
            "allowed_count": len(res.allowed_all),
            "strong_count": len(res.hits),
            "acl_filtered_at": res.acl_filtered_at,
            "label": gen.get("label"),
            "degraded": degraded,
        }

    # refuse correctness
    if item.expect_status == "refuse":
        refuse_ok = actual_status == "refuse" and actual_reason == item.expect_reason
    else:
        refuse_ok = actual_status == "ok" and actual_reason is None

    # citation coverage (only when answer expected)
    citation_ok: bool | None = None
    if item.expect_status == "ok" and item.require_citations:
        citation_ok = bool(citations) and all(bool(c.get("chunk_id")) for c in citations)

    # answer heuristic (only when answer expected and we got an answer)
    heuristic_ok: bool | None = None
    heuristic_score: float | None = None
    if item.expect_status == "ok" and actual_status == "ok":
        heuristic_ok, heuristic_score = answer_heuristic(item.query, answer, citations)

    return CaseResult(
        id=item.id,
        category=item.category,
        query=item.query,
        role=item.role,
        expect_status=item.expect_status,
        expect_reason=item.expect_reason,
        actual_status=actual_status,
        actual_reason=actual_reason,
        refuse_ok=refuse_ok,
        citation_ok=citation_ok,
        heuristic_ok=heuristic_ok,
        heuristic_score=heuristic_score,
        citations=[str(c.get("chunk_id")) for c in citations if c.get("chunk_id")],
        mode=mode,
        degraded=degraded,
        details=details,
    )


def aggregate(results: Iterable[CaseResult]) -> dict[str, Any]:
    """Compute honest metrics from this run only (no invented numbers)."""
    rows = list(results)
    n = len(rows)
    refuse_n = sum(1 for r in rows if r.refuse_ok)
    cite_applicable = [r for r in rows if r.citation_ok is not None]
    cite_ok = sum(1 for r in cite_applicable if r.citation_ok)
    heur_applicable = [r for r in rows if r.heuristic_ok is not None]
    heur_ok = sum(1 for r in heur_applicable if r.heuristic_ok)

    by_cat: dict[str, dict[str, Any]] = {}
    for cat, group in _group_by(rows, lambda r: r.category).items():
        g_refuse = sum(1 for r in group if r.refuse_ok)
        by_cat[cat] = {
            "n": len(group),
            "refuse_correct": g_refuse,
            "refuse_correctness": round(g_refuse / len(group), 4) if group else None,
        }

    failures = [
        {
            "id": r.id,
            "category": r.category,
            "expect": {"status": r.expect_status, "reason": r.expect_reason},
            "actual": {"status": r.actual_status, "reason": r.actual_reason},
            "refuse_ok": r.refuse_ok,
            "citation_ok": r.citation_ok,
        }
        for r in rows
        if (not r.refuse_ok) or (r.citation_ok is False)
    ]

    return {
        "n": n,
        "refuse_correctness": {
            "correct": refuse_n,
            "total": n,
            "rate": round(refuse_n / n, 4) if n else None,
            "definition": "expected refuse/ok (+ reason) matches actual for this run",
        },
        "citation_coverage": {
            "correct": cite_ok,
            "total": len(cite_applicable),
            "rate": round(cite_ok / len(cite_applicable), 4) if cite_applicable else None,
            "definition": "when answer expected, every citation has chunk_id (this run only)",
        },
        "answer_heuristic": {
            "correct": heur_ok,
            "total": len(heur_applicable),
            "rate": round(heur_ok / len(heur_applicable), 4) if heur_applicable else None,
            "label": "heuristic - NOT accuracy",
            "definition": "simple query/evidence token overlap >= 0.15; not marketed as accuracy",
        },
        "by_category": by_cat,
        "category_counts": dict(Counter(r.category for r in rows)),
        "failures": failures,
        "failure_count": len(failures),
    }


def _group_by(rows: list[CaseResult], key) -> dict[str, list[CaseResult]]:
    out: dict[str, list[CaseResult]] = {}
    for r in rows:
        out.setdefault(key(r), []).append(r)
    return out


def run_eval(
    gold_path: Path | str,
    *,
    index_dir: Path | str,
    force_degraded: bool = True,
    limit: int | None = None,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Run offline eval and return metrics + per-case results.

    Default ``force_degraded=True`` clears OPENAI_API_KEY for this process so
    the path is DEGRADED / no-LLM. Set False only for optional experimental
    live LLM (labeled not_real_api — not production API eval).
    """
    gold = load_gold(gold_path)
    if categories:
        allow = {c.lower() for c in categories}
        gold = [g for g in gold if g.category.lower() in allow]
    if limit is not None:
        gold = gold[: max(0, int(limit))]

    idx = Path(index_dir)
    results = [
        run_one(item, index_dir=idx, force_degraded=force_degraded) for item in gold
    ]
    metrics = aggregate(results)

    eval_mode = EVAL_MODE_DEGRADED if force_degraded else EVAL_MODE_LIVE_EXPERIMENTAL
    honesty = {
        "eval_mode": eval_mode,
        "default_path": EVAL_MODE_DEGRADED,
        "live_llm": None
        if force_degraded
        else {
            "marker": NOT_REAL_API,
            "note": (
                "Optional experimental live LLM path. Not a validated production "
                "API eval. Metrics still computed from this run only."
            ),
        },
        "metrics_source": "computed_from_this_run_only",
        "no_hardcoded_accuracy": True,
        "degraded_label": DEGRADED_LABEL,
    }

    return {
        "honesty": honesty,
        "gold_path": str(Path(gold_path)),
        "index_dir": str(idx),
        "gold_count": len(gold),
        "metrics": metrics,
        "results": [asdict(r) for r in results],
    }


def format_report(report: dict[str, Any]) -> str:
    """Human-readable report (numbers from report only)."""
    h = report.get("honesty") or {}
    m = report.get("metrics") or {}
    lines = [
        "=== DocPilot Milestone D offline eval ===",
        f"eval_mode={h.get('eval_mode')}",
        f"metrics_source={h.get('metrics_source')}",
        f"gold_path={report.get('gold_path')}",
        f"index_dir={report.get('index_dir')}",
        f"gold_count={report.get('gold_count')}",
        f"category_counts={m.get('category_counts')}",
        "",
        "-- refuse_correctness (this run) --",
        json.dumps(m.get("refuse_correctness"), ensure_ascii=False),
        "",
        "-- citation_coverage (this run) --",
        json.dumps(m.get("citation_coverage"), ensure_ascii=False),
        "",
        "-- answer_heuristic (NOT accuracy; this run) --",
        json.dumps(m.get("answer_heuristic"), ensure_ascii=False),
        "",
        "-- by_category --",
        json.dumps(m.get("by_category"), ensure_ascii=False, indent=2),
        "",
        f"failure_count={m.get('failure_count')}",
    ]
    failures = m.get("failures") or []
    if failures:
        lines.append("failures:")
        for f in failures:
            lines.append(f"  {f}")
    live = h.get("live_llm")
    if live:
        lines.append("")
        lines.append(f"LIVE PATH MARKER: {live.get('marker')} — {live.get('note')}")
    return "\n".join(lines)
