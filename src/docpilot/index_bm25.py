"""Real BM25 lexical index using ``rank_bm25.BM25Okapi``.

Persists under ``indexes/`` (gitignored):
- ``bm25_meta.json`` — chunk metadata + tokenized corpus mirror
- ``bm25_tokens.pkl`` — tokenized documents for BM25Okapi rebuild on load

Build + load + search APIs. Scores are raw BM25 (not fabricated metrics).
"""

from __future__ import annotations

import json
import pickle
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)

META_NAME = "bm25_meta.json"
TOKENS_NAME = "bm25_tokens.pkl"


def tokenize(text: str) -> list[str]:
    """Simple alphanumeric tokenizer (lowercase)."""
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class BM25Index:
    """In-memory BM25 with disk persistence."""

    def __init__(self, chunks: list[dict[str, Any]], tokenized: list[list[str]] | None = None):
        self.chunks = chunks
        self.tokenized = tokenized if tokenized is not None else [tokenize(c.get("text", "")) for c in chunks]
        if not self.tokenized:
            # BM25Okapi needs at least one doc; keep a sentinel empty corpus.
            self._bm25: BM25Okapi | None = None
        else:
            self._bm25 = BM25Okapi(self.tokenized)

    @property
    def size(self) -> int:
        return len(self.chunks)

    def search(self, query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        """Return top_k hits with raw BM25 scores (honest, not normalized MRR)."""
        if not self.chunks or self._bm25 is None:
            return []
        q = tokenize(query)
        if not q:
            return []
        scores = self._bm25.get_scores(q)
        ranked = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
        hits: list[dict[str, Any]] = []
        for i in ranked[: max(0, top_k)]:
            score = float(scores[i])
            if score <= 0:
                continue
            chunk = dict(self.chunks[i])
            chunk["score"] = score
            chunk["rank"] = len(hits) + 1
            hits.append(chunk)
        return hits

    def save(self, index_dir: Path) -> Path:
        index_dir = Path(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "backend": "rank_bm25.BM25Okapi",
            "chunk_count": len(self.chunks),
            "chunks": self.chunks,
        }
        meta_path = index_dir / META_NAME
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        tokens_path = index_dir / TOKENS_NAME
        with tokens_path.open("wb") as f:
            pickle.dump(self.tokenized, f, protocol=pickle.HIGHEST_PROTOCOL)
        return meta_path

    @classmethod
    def load(cls, index_dir: Path) -> "BM25Index":
        index_dir = Path(index_dir)
        meta_path = index_dir / META_NAME
        tokens_path = index_dir / TOKENS_NAME
        if not meta_path.is_file():
            raise FileNotFoundError(f"BM25 meta not found: {meta_path}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        chunks = meta.get("chunks") or []
        if tokens_path.is_file():
            with tokens_path.open("rb") as f:
                tokenized = pickle.load(f)
        else:
            tokenized = [tokenize(c.get("text", "")) for c in chunks]
        return cls(chunks, tokenized=tokenized)


def build_bm25_index(chunks: list[dict[str, Any]], index_dir: Path) -> BM25Index:
    """Build and persist a BM25 index; return the in-memory index."""
    index = BM25Index(chunks)
    index.save(Path(index_dir))
    return index


def load_bm25_index(index_dir: Path) -> BM25Index:
    """Load a previously persisted BM25 index."""
    return BM25Index.load(Path(index_dir))


def search_bm25(query: str, index_dir: Path, *, top_k: int = 5) -> list[dict[str, Any]]:
    """Search a persisted BM25 index."""
    return load_bm25_index(index_dir).search(query, top_k=top_k)
