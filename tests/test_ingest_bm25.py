"""Smoke tests for Milestone B: ingest → chunk → BM25."""

from __future__ import annotations

from pathlib import Path

from docpilot.chunking import chunk_documents
from docpilot.index_bm25 import build_bm25_index, load_bm25_index, search_bm25
from docpilot.index_vector import NOT_REAL_EMBEDDINGS, build_vector_index, not_real_embeddings
from docpilot.ingest import ingest_directory, ingest_path

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "data" / "sample_docs"


def test_ingest_sample_docs_have_acl_and_fixture_label():
    docs = ingest_directory(SAMPLE)
    assert len(docs) >= 2
    by_id = {d["doc_id"]: d for d in docs}
    assert "fixture-acl-faq" in by_id
    faq = by_id["fixture-acl-faq"]
    assert faq["label"] == "FIXTURE"
    assert "eng" in faq["allowed_roles"]
    assert faq["format"] == "md"
    assert faq["char_count"] > 0


def test_chunk_stable_ids_and_offsets():
    docs = ingest_directory(SAMPLE)
    chunks = chunk_documents(docs)
    assert len(chunks) >= len(docs)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
    for c in chunks:
        assert c["chunk_id"].startswith(c["doc_id"] + "::")
        assert c["source_path"]
        assert isinstance(c["char_start"], int)
        assert c["char_end"] >= c["char_start"]


def test_bm25_build_load_search():
    # Use repo-local dir (Windows agents may lack permission on pytest's default tmp).
    index_dir = REPO / "indexes" / "_pytest_bm25"
    if index_dir.exists():
        for p in index_dir.glob("*"):
            p.unlink()
    else:
        index_dir.mkdir(parents=True, exist_ok=True)
    docs = ingest_directory(SAMPLE)
    chunks = chunk_documents(docs)
    built = build_bm25_index(chunks, index_dir)
    assert built.size == len(chunks)
    loaded = load_bm25_index(index_dir)
    assert loaded.size == built.size
    hits = loaded.search("ACL refuse unauthorized", top_k=5)
    assert isinstance(hits, list)
    # Honest: structure + at least one positive hit for fixture terms — not recall/MRR.
    assert len(hits) >= 1
    assert "chunk_id" in hits[0]
    assert hits[0]["score"] > 0
    via_api = search_bm25("onboarding laptop", index_dir, top_k=3)
    assert isinstance(via_api, list)


def test_vector_stub_marked():
    assert not_real_embeddings is True
    docs = ingest_directory(SAMPLE)
    chunks = chunk_documents(docs)
    out = REPO / "indexes" / "_pytest_vector"
    out.mkdir(parents=True, exist_ok=True)
    stat = build_vector_index(chunks, out)
    assert stat[NOT_REAL_EMBEDDINGS] is True
    assert stat["status"] == "stub"


def test_ingest_single_fixture_path():
    path = SAMPLE / "fixture_acl_faq.md"
    doc = ingest_path(path, root=SAMPLE)
    assert doc["doc_id"] == "fixture-acl-faq"
