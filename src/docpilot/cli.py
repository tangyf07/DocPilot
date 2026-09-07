"""DocPilot CLI entry (Typer).

Milestone A: stub commands only — no real ingest/ask pipeline.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="DocPilot — ACL-aware document Q&A (stubs in Milestone A).")


@app.callback()
def main() -> None:
    """DocPilot CLI. Pipeline not implemented until later milestones."""


@app.command("status")
def status() -> None:
    """Show Milestone A skeleton status."""
    typer.echo("DocPilot Milestone A: skeleton only. ingest/retrieve/generate are stubs.")
    typer.echo("This is NOT DataPilot (NL→SQL).")


@app.command("ingest")
def ingest_cmd(path: str = typer.Argument(..., help="Path to ingest")) -> None:
    """STUB: ingest not implemented."""
    typer.echo(f"STUB: ingest not implemented (path={path}). See Milestone B+.")
    raise typer.Exit(code=2)


@app.command("ask")
def ask_cmd(question: str = typer.Argument(..., help="Question to ask")) -> None:
    """STUB: ask not implemented."""
    typer.echo(f"STUB: ask not implemented (question={question!r}). See Milestone B+.")
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()