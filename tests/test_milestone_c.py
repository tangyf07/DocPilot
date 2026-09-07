"""Milestone C smoke tests: ACL-at-retrieve, citations, three refuse paths."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from docpilot.acl import caller_may_read, filter_chunks
from docpilot.chunking import chunk_documents
from docpilot.generate import DEGRADED_LABEL, generate_answer, generate_extractive
from docpilot.index_bm25 import build_bm25_index
from docpilot.ingest import ingest_directory
from docpilot.refuse import (
    REASON_NO_HITS,
    REASON_UNAUTHORIZED,
    REASON_WEAK_EVIDENCE,
    classify_retrieve,
    refuse_from_retrieve,
)
from docpilot.retrieve import retrieve

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "data" / "sample_docs"
INDEX = REPO / "indexes" / "_pytest_c"


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


def test_acl_role_intersection():
    chunk = {"allowed_roles": ["eng", "docs"]}
    assert caller_may_read({"role": "eng"}, chunk) is True
    assert caller_may_read({"role": "hr"}, chunk) is False
    assert caller_may_read({"role": "ENG"}, chunk) is True  # case-insensitive
    assert caller_may_read({"roles": ["docs"]}, chunk) is True
    assert caller_may_read({}, chunk) is False


def test_acl_filter_at_retrieve_not_post_gen(bm25_index_dir: Path):
    """Authorized hits only; ACL applied in retrieve (acl_filtered_at=retrieve)."""
    res = retrieve(
        "ACL refuse unauthorized",
        caller={"role": "eng"},
        index_dir=bm25_index_dir,
        top_k=5,
        min_score=0.01,
    )
    assert res.acl_filtered_at == "retrieve"
    assert res.raw_count >= 1
    assert res.hits
    for h in res.hits:
        assert "eng" in [r.lower() for r in (h.get("allowed_roles") or [])] or caller_may_read(
            {"role": "eng"}, h
        )
    # outsider: raw hits exist but authorized empty -> unauthorized path
    denied = retrieve(
        "ACL refuse unauthorized",
        caller={"role": "contractor"},
        index_dir=bm25_index_dir,
        top_k=5,
        min_score=0.01,
    )
    assert denied.raw_count >= 1
    assert denied.acl_dropped >= 1
    assert denied.allowed_all == []
    assert denied.hits == []
    assert denied.acl_filtered_at == "retrieve"
    assert classify_retrieve(denied) == REASON_UNAUTHORIZED


def test_refuse_unauthorized(bm25_index_dir: Path):
    res = retrieve(
        "ACL refuse unauthorized",
        caller={"role": "intern"},
        index_dir=bm25_index_dir,
        min_score=0.01,
    )
    out = refuse_from_retrieve(res)
    assert out is not None
    assert out["status"] == "refuse"
    assert out["reason"] == REASON_UNAUTHORIZED
    assert out["answer"] is None
    assert out["details"]["acl_filtered_at"] == "retrieve"


def test_refuse_no_hits(bm25_index_dir: Path):
    res = retrieve(
        "xyzzyqwertynonexistent999zzz",
        caller={"role": "eng"},
        index_dir=bm25_index_dir,
        min_score=0.01,
    )
    assert res.raw_count == 0
    out = refuse_from_retrieve(res)
    assert out is not None
    assert out["reason"] == REASON_NO_HITS


def test_refuse_weak_evidence(bm25_index_dir: Path):
    """Distinct from no_hits: authorized BM25 hits exist but below threshold."""
    res = retrieve(
        "ACL refuse",
        caller={"role": "eng"},
        index_dir=bm25_index_dir,
        min_score=1000.0,  # impossibly high -> all allowed hits are "weak"
    )
    assert res.raw_count >= 1
    assert res.allowed_all  # authorized evidence exists
    assert res.hits == []  # none strong enough
    out = refuse_from_retrieve(res)
    assert out is not None
    assert out["reason"] == REASON_WEAK_EVIDENCE


def test_success_with_citations_degraded(bm25_index_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    res = retrieve(
        "What is ACL refuse behavior in DocPilot?",
        caller={"role": "eng"},
        index_dir=bm25_index_dir,
        top_k=3,
        min_score=0.01,
    )
    assert classify_retrieve(res) is None
    assert res.hits
    gen = generate_answer("What is ACL refuse behavior in DocPilot?", res.hits)
    assert gen["status"] == "ok"
    assert gen["degraded"] is True
    assert DEGRADED_LABEL in (gen.get("label") or "")
    assert gen["citations"]
    for c in gen["citations"]:
        assert c.get("chunk_id")
        assert c.get("source_path")
    # extractive path must not invent chunk ids
    known = {h["chunk_id"] for h in res.hits}
    for c in gen["citations"]:
        assert c["chunk_id"] in known


def test_generate_extractive_no_invent():
    chunks = [
        {
            "chunk_id": "fixture-acl-faq::chunk-0003",
            "doc_id": "fixture-acl-faq",
            "source_path": "fixture_acl_faq.md",
            "text": "DocPilot should refuse rather than invent content.",
            "score": 2.0,
            "section_heading": "Refuse behavior",
        }
    ]
    out = generate_extractive("refuse?", chunks)
    assert out["degraded"] is True
    assert out["citations"][0]["chunk_id"] == "fixture-acl-faq::chunk-0003"
    assert "invent" in out["answer"].lower() or "refuse" in out["answer"].lower()


def test_filter_chunks_helper():
    chunks = [
        {"chunk_id": "a", "allowed_roles": ["eng"]},
        {"chunk_id": "b", "allowed_roles": ["hr"]},
        {"chunk_id": "c", "allowed_roles": ["public"]},
    ]
    kept = filter_chunks({"role": "eng"}, chunks)
    assert [c["chunk_id"] for c in kept] == ["a"]
