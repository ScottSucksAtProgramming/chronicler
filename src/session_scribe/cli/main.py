"""Session Scribe CLI — entry point for all user interaction."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="scribe",
    help="D&D Session Scribe — AI-powered campaign note management.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print("session-scribe v0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """D&D Session Scribe — AI-powered campaign note management."""


@app.command()
def ingest(
    files: Annotated[
        list[Path],
        typer.Argument(help="PLAUD PDF summary and/or transcript .txt files to ingest."),
    ],
    session_number: Annotated[
        Optional[int],
        typer.Option("--session", "-s", help="Session number. Auto-detected if not provided."),
    ] = None,
) -> None:
    """Ingest PLAUD session files into the campaign vault."""
    console.print(f"[bold]Ingesting {len(files)} file(s)...[/bold]")
    for f in files:
        if not f.exists():
            console.print(f"[red]Error: File not found: {f}[/red]")
            raise typer.Exit(1)
        console.print(f"  - {f.name}")
    console.print("[yellow]Ingestion pipeline not yet implemented.[/yellow]")


@app.command()
def chat() -> None:
    """Open interactive campaign Q&A chat."""
    console.print("[yellow]Chat TUI not yet implemented.[/yellow]")


@app.command()
def review() -> None:
    """Run a quality review pass over the vault."""
    console.print("[yellow]Reviewer not yet implemented.[/yellow]")


@app.command()
def ask() -> None:
    """Review and answer the agent's pending questions."""
    console.print("[yellow]Question queue not yet implemented.[/yellow]")


@app.command()
def reindex() -> None:
    """Rebuild the vector store index from current vault contents."""
    console.print("[yellow]Reindexing not yet implemented.[/yellow]")


@app.command()
def config() -> None:
    """Show current configuration and verify setup."""
    try:
        from session_scribe.config.settings import Settings

        settings = Settings()
        console.print("[bold]Session Scribe Configuration[/bold]")
        console.print(f"  Vault path:       {settings.vault_path}")
        console.print(f"  nano-gpt model:   {settings.nanogpt_model}")
        console.print(f"  LM Studio URL:    {settings.lm_studio_base_url}")
        console.print(f"  Embedding model:  {settings.embedding_model}")
        console.print(f"  Log level:        {settings.log_level}")

        if not settings.vault_path.exists():
            console.print(f"\n[yellow]Warning: Vault path does not exist: {settings.vault_path}[/yellow]")
        else:
            console.print("\n[green]Vault path exists.[/green]")
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\nCopy .env.example to .env and fill in your values:")
        console.print("  cp .env.example .env")
        raise typer.Exit(1)


@app.command()
def stats() -> None:
    """Show LLM usage statistics and cost tracking."""
    console.print("[bold]Session Scribe Stats[/bold]")
    console.print("No usage data yet.")
