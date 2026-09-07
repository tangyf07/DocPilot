"""DocPilot CLI (Typer) — Milestone B: ingest + BM25 index + smoke query.

Milestone C (ACL-at-retrieve / generate-with-citations) is NOT implemented.
``bm25-query`` is a raw lexical smoke helper over the persisted BM25 index only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from docpilot.chunking import chunk_documents
from docpilot.index_bm25 import build_bm25_index, load_bm25_index
from docpilot.index_vector import NOT_REAL_EMBEDDINGS, build_vector_index
from docpilot.ingest import ingest_directory, list_skipped_pdfs

app = typer.Typer(help="DocPilot — ACL-aware document Q&A (Milestone B: ingest/index).")


def _default_data_dir() -> Path:
    return Path("data/sample_docs")


def _default_index_dir() -> Path:
    return Path("indexes")


@app.callback()
def main() -> None:
    """DocPilot CLI."""


@app.command("status")
def status() -> None:
    """Show current milestone status."""
    typer.echo("DocPilot Milestone B: MD ingest → chunk → BM25 index (real).")
    typer.echo(f"Vector index: STUB ({NOT_REAL_EMBEDDINGS}=True).")
    typer.echo("Milestone C (ACL retrieve / generate) not implemented.")
    typer.echo("This is NOT DataPilot (NL→SQL).")


@app.command("ingest")
def ingest_cmd(
    path: Optional[str] = typer.Argument(
        None,
        help="Docs root (default: data/sample_docs or DOCPILOT_DATA_DIR)",
    ),
    index_dir: Optional[str] = typer.Option(
        None,
        "--index-dir",
        help="Index output dir (default: indexes or DOCPILOT_INDEX_DIR)",
    ),
    skip_vector_stub: bool = typer.Option(
        False,
        "--skip-vector-stub",
        help="Do not write the vector stub marker file",
    ),
) -> None:
    """Ingest Markdown, chunk, build BM25 (+ optional vector stub metadata)."""
    import os

    data_root = Path(path or os.environ.get("DOCPILOT_DATA_DIR") or _default_data_dir())
    out_dir = Path(index_dir or os.environ.get("DOCPILOT_INDEX_DIR") or _default_index_dir())

    if not data_root.is_dir():
        typer.echo(f"ERROR: data dir not found: {data_root}", err=True)
        raise typer.Exit(code=1)

    docs = ingest_directory(data_root)
    skipped_pdfs = list_skipped_pdfs(data_root)
    chunks = chunk_documents(docs)
    bm25 = build_bm25_index(chunks, out_dir / "bm25")

    typer.echo(f"data_root={data_root}")
    typer.echo(f"index_dir={out_dir}")
    typer.echo(f"docs={len(docs)}")
    typer.echo(f"chunks={len(chunks)}")
    typer.echo(f"bm25_chunks={bm25.size}")
    if skipped_pdfs:
        typer.echo(f"skipped_pdfs={len(skipped_pdfs)} (PDF ingest not implemented)")
        for p in skipped_pdfs:
            typer.echo(f"  - {p}")

    if not skip_vector_stub:
        vstat = build_vector_index(chunks, out_dir / "vector")
        typer.echo(
            f"vector_stub={vstat.get('status')} {NOT_REAL_EMBEDDINGS}={vstat.get(NOT_REAL_EMBEDDINGS)}"
        )


@app.command("bm25-query")
def bm25_query_cmd(
    query: str = typer.Argument(..., help="Lexical query for BM25 smoke search"),
    index_dir: Optional[str] = typer.Option(
        None,
        "--index-dir",
        help="Index dir containing bm25/ (default: indexes)",
    ),
    top_k: int = typer.Option(5, "--top-k", help="Max hits to print"),
) -> None:
    """Smoke-query the persisted BM25 index (not full ACL retrieve / generate)."""
    import os

    root = Path(index_dir or os.environ.get("DOCPILOT_INDEX_DIR") or _default_index_dir())
    bm25_dir = root / "bm25" if (root / "bm25").is_dir() else root
    try:
        index = load_bm25_index(bm25_dir)
    except FileNotFoundError as e:
        typer.echo(f"ERROR: {e}", err=True)
        typer.echo("Run: python -m docpilot.cli ingest", err=True)
        raise typer.Exit(code=1)

    hits = index.search(query, top_k=top_k)
    typer.echo(f"query={query!r} bm25_size={index.size} hits={len(hits)}")
    for h in hits:
        typer.echo(
            f"  rank={h.get('rank')} score={h.get('score'):.4f} "
            f"chunk_id={h.get('chunk_id')} path={h.get('source_path')} "
            f"section={h.get('section_heading')!r}"
        )
    if not hits:
        typer.echo("  (no positive-score hits)")


@app.command("ask")
def ask_cmd(question: str = typer.Argument(..., help="Question to ask")) -> None:
    """STUB: full ask (ACL retrieve + generate) is Milestone C — not implemented."""
    typer.echo(
        f"STUB: ask/generate not implemented (Milestone C). "
        f"For BM25 smoke use: docpilot bm25-query {question!r}"
    )
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
