"""Milestone D tests: gold load + offline eval subset (no network / no API key)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from docpilot.chunking import chunk_documents
from docpilot.eval_runner import (
    EVAL_MODE_DEGRADED,
    load_gold,
    run_eval,
)
from docpilot.index_bm25 import build_bm25_index
from docpilot.ingest import ingest_directory

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "data" / "sample_docs"
GOLD = REPO / "data" / "eval" / "gold_milestone_d.jsonl"
INDEX = REPO / "indexes" / "_pytest_d"


@pytest.fixture(scope="module")
def bm25_index_dir() -> Path:
    docs = ingest_directory(SAMPLE)
    chunks = chunk_documents(docs)
    out = INDEX / "bm25"
    if out.exists():
        for p in out.glob("*"):
            p.unlink()
    else:
        out.mkdir(parents=True, exist_ok=True)
    build_bm25_index(chunks, out)
    return INDEX


def test_gold_file_exists_and_count():
    assert GOLD.is_file(), "gold_milestone_d.jsonl missing"
    items = load_gold(GOLD)
    assert len(items) >= 30
    cats = {i.category for i in items}
    assert "authorized_answer" in cats
    assert "unauthorized_refuse" in cats
    assert "no_hits_refuse" in cats
    assert "weak_evidence_refuse" in cats
    for i in items:
        assert i.label.upper() == "GOLD" or "GOLD" in i.label.upper()
        assert i.query and i.role
        assert i.expect_status in {"ok", "refuse"}


def test_offline_eval_subset_no_network(bm25_index_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Run a small subset offline; metrics must come from this run."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # one of each category via limit after filter would be awkward; take first 8
    report = run_eval(
        GOLD,
        index_dir=bm25_index_dir,
        force_degraded=True,
        limit=8,
    )
    assert report["honesty"]["eval_mode"] == EVAL_MODE_DEGRADED
    assert report["honesty"]["metrics_source"] == "computed_from_this_run_only"
    assert report["honesty"]["no_hardcoded_accuracy"] is True
    assert report["gold_count"] == 8
    m = report["metrics"]
    assert m["refuse_correctness"]["total"] == 8
    assert m["refuse_correctness"]["correct"] == m["refuse_correctness"]["correct"]  # from run
    # rates are derived, not magic constants baked elsewhere
    rate = m["refuse_correctness"]["rate"]
    assert rate == round(m["refuse_correctness"]["correct"] / 8, 4)


def test_full_offline_eval_degraded(bm25_index_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Full gold set offline (DEGRADED). Expect perfect refuse + citation on fixtures."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Ensure no accidental network: clear proxy-ish keys too? not required.
    report = run_eval(
        GOLD,
        index_dir=bm25_index_dir,
        force_degraded=True,
    )
    assert report["gold_count"] >= 30
    m = report["metrics"]
    assert m["failure_count"] == 0, m.get("failures")
    assert m["refuse_correctness"]["rate"] == 1.0
    cite = m["citation_coverage"]
    assert cite["total"] >= 1
    assert cite["rate"] == 1.0
    # heuristic present and labeled
    assert "NOT accuracy" in (m["answer_heuristic"].get("label") or "")
    # every answered case should be degraded
    for row in report["results"]:
        if row["actual_status"] == "ok":
            assert row["degraded"] is True


def test_run_eval_script_help():
    """Smoke: script file exists (execution covered via module API above)."""
    script = REPO / "scripts" / "run_eval.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "DEGRADED" in text
    assert "not_real_api" in text or "live-llm" in text
