"""DocPilot CLI (Typer) — Milestone C: ACL retrieve + generate/refuse + ask.

Milestone B commands (ingest / bm25-query) remain. Vector stays stub-only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import typer

from docpilot.chunking import chunk_documents
from docpilot.generate import DEGRADED_LABEL, generate_answer
from docpilot.index_bm25 import build_bm25_index, load_bm25_index
from docpilot.index_vector import NOT_REAL_EMBEDDINGS, build_vector_index
from docpilot.ingest import ingest_directory, list_skipped_pdfs
from docpilot.refuse import refuse_from_retrieve
from docpilot.retrieve import DEFAULT_REFUSE_THRESHOLD, retrieve

app = typer.Typer(help="DocPilot — ACL-aware document Q&A (Milestone C: ask/retrieve/refuse).")


def _default_data_dir() -> Path:
    return Path("data/sample_docs")


def _default_index_dir() -> Path:
    return Path("indexes")


def _load_dotenv() -> None:
    """Load .env if present (optional)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = Path(".env")
    if env_path.is_file():
        load_dotenv(env_path)


@app.callback()
def main() -> None:
    """DocPilot CLI."""
    _load_dotenv()


@app.command("status")
def status() -> None:
    """Show current milestone status."""
    typer.echo("DocPilot Milestone C: ACL-at-retrieve + generate-with-citations + refuse.")
    typer.echo(f"Vector index: STUB ({NOT_REAL_EMBEDDINGS}=True).")
    typer.echo("BM25 + ACL retrieve; ask --role end-to-end.")
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
    """Smoke-query the persisted BM25 index (no ACL; use ``ask`` for ACL retrieve)."""
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
            f"roles={h.get('allowed_roles')} section={h.get('section_heading')!r}"
        )
    if not hits:
        typer.echo("  (no positive-score hits)")


def _print_ask_result(result: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    status = result.get("status")
    if status == "refuse":
        typer.echo(f"status=refuse reason={result.get('reason')}")
        typer.echo(result.get("message") or "")
        details = result.get("details") or {}
        typer.echo(
            f"details: raw_count={details.get('raw_count')} "
            f"acl_dropped={details.get('acl_dropped')} "
            f"allowed={details.get('allowed_count')} "
            f"strong={details.get('strong_count')} "
            f"acl_filtered_at={details.get('acl_filtered_at')}"
        )
        return
    typer.echo(f"status={status} mode={result.get('mode')} degraded={result.get('degraded')}")
    if result.get("degraded") or result.get("label"):
        typer.echo(f"label={result.get('label') or DEGRADED_LABEL}")
    typer.echo("--- answer ---")
    typer.echo(result.get("answer") or "")
    typer.echo("--- citations ---")
    for c in result.get("citations") or []:
        typer.echo(
            f"  chunk_id={c.get('chunk_id')} source={c.get('source_path')} "
            f"score={c.get('score')}"
        )


@app.command("ask")
def ask_cmd(
    question: str = typer.Argument(..., help="Question to ask"),
    role: str = typer.Option(..., "--role", help="Caller role for ACL-at-retrieve"),
    index_dir: Optional[str] = typer.Option(
        None,
        "--index-dir",
        help="Index dir (default: indexes or DOCPILOT_INDEX_DIR)",
    ),
    top_k: int = typer.Option(5, "--top-k", help="Max authorized chunks for generation"),
    refuse_threshold: Optional[float] = typer.Option(
        None,
        "--refuse-threshold",
        help=f"Min BM25 score for strong evidence (default: env or {DEFAULT_REFUSE_THRESHOLD})",
    ),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """ACL-aware ask: retrieve (role filter) → generate-with-citations or refuse.

    Without OPENAI_API_KEY, answers use degraded extractive / citation-only mode
    clearly labeled DEGRADED / no-LLM.
    """
    root = Path(index_dir or os.environ.get("DOCPILOT_INDEX_DIR") or _default_index_dir())
    caller = {"role": role}
    try:
        result = retrieve(
            question,
            caller=caller,
            index_dir=root,
            top_k=top_k,
            min_score=refuse_threshold,
        )
    except FileNotFoundError as e:
        typer.echo(f"ERROR: {e}", err=True)
        typer.echo("Run: python -m docpilot.cli ingest", err=True)
        raise typer.Exit(code=1)

    refused = refuse_from_retrieve(result)
    if refused is not None:
        refused["role"] = role
        refused["acl_filtered_at"] = result.acl_filtered_at
        _print_ask_result(refused, as_json=as_json)
        raise typer.Exit(code=0)

    gen = generate_answer(question, result.hits)
    gen["role"] = role
    gen["retrieve"] = {
        "raw_count": result.raw_count,
        "acl_dropped": result.acl_dropped,
        "allowed_count": len(result.allowed_all),
        "strong_count": len(result.hits),
        "acl_filtered_at": result.acl_filtered_at,
        "min_score": result.min_score,
        "backend": result.backend,
    }
    _print_ask_result(gen, as_json=as_json)


if __name__ == "__main__":
    app()
