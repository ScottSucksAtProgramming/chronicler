"""Session Scribe CLI — entry point for all user interaction."""

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from session_scribe.config.settings import Settings
from session_scribe.vault.obsidian_cli import ObsidianCLI
from session_scribe.vault.vault_manager import VaultManager

app = typer.Typer(
    name="scribe",
    help="D&D Session Scribe — AI-powered campaign note management.",
    no_args_is_help=True,
)
console = Console()


class _ConfigError(Exception):
    """Raised when Settings cannot be loaded."""


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


async def _run_ingest_pipeline(
    files: list[Path],
    session_number: int,
    pdf_files: list[Path],
    txt_files: list[Path],
) -> "ExtractionResult":
    """Async helper that runs the full ingestion and extraction pipeline."""
    from session_scribe.extraction.extractor import extract_session
    from session_scribe.gateway.llm_gateway import LLMGateway
    from session_scribe.ingestion.normalizer import normalize_session
    from session_scribe.ingestion.pdf_parser import parse_plaud_pdf
    from session_scribe.ingestion.transcript_parser import parse_transcript
    from session_scribe.models.context import ContextBundle

    try:
        settings = Settings()
    except Exception as exc:
        from pydantic import ValidationError
        if isinstance(exc, ValidationError):
            missing = [err["loc"][0] for err in exc.errors() if err["type"] == "missing"]
            if missing:
                env_vars = [f"SCRIBE_{name.upper()}" for name in missing]
                raise _ConfigError(f"missing required setting(s): {', '.join(env_vars)}") from exc
        raise _ConfigError(str(exc)) from exc

    gateway = LLMGateway(settings)

    try:
        # Step 1: Parse PDF (if provided)
        parsed_pdf = None
        if pdf_files:
            console.print("[cyan]Parsing PDF...[/cyan]")
            parsed_pdf = parse_plaud_pdf(pdf_files[0])

        # Step 2: Parse transcript (if provided)
        transcript_segments = None
        if txt_files:
            console.print("[cyan]Parsing transcript...[/cyan]")
            raw_text = txt_files[0].read_text(encoding="utf-8")
            transcript_segments = parse_transcript(raw_text)

        # Step 2b: Create VaultManager and get context from vault
        if settings.vault_name:
            cli = ObsidianCLI(settings.vault_name)
            vault_manager = VaultManager(cli)
            try:
                console.print("[cyan]Loading campaign context from vault...[/cyan]")
                context = vault_manager.get_context_bundle(session_number)
            except Exception:
                # Vault may not be initialized yet — fall back to empty context
                context = ContextBundle(session_number=session_number)
        else:
            vault_manager = None
            context = ContextBundle(session_number=session_number)

        # Determine model name based on provider
        model = (
            settings.kimi_model or "kimi-default"
            if settings.llm_provider == "kimi"
            else settings.nanogpt_model
        )

        # Step 3: Normalize session (includes banter filtering)
        console.print("[cyan]Filtering banter...[/cyan]")
        normalized = await normalize_session(
            session_number=session_number,
            parsed_pdf=parsed_pdf,
            transcript_segments=transcript_segments,
            gateway=gateway,
            model=model,
        )

        # Step 4: Extract entities (with campaign context)
        console.print("[cyan]Extracting entities...[/cyan]")
        result = await extract_session(
            session=normalized,
            context=context,
            gateway=gateway,
            model=model,
        )

        # Step 5: Write extraction result to vault
        if vault_manager is not None:
            try:
                console.print("[cyan]Writing notes to vault...[/cyan]")
                vault_manager.write_extraction_result(result)
                total = (
                    len(result.npcs)
                    + len(result.locations)
                    + len(result.factions)
                    + len(result.loot)
                    + 1  # session note
                )
                console.print(
                    f"[green]Notes written to vault:[/green] {total} notes created/updated"
                )
            except Exception as exc:
                console.print(
                    f"[yellow]Warning: Could not write to vault: {exc}[/yellow]"
                )

        return result
    finally:
        await gateway.close()


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
    # --- Validate files ---
    console.print(f"[bold]Ingesting {len(files)} file(s)...[/bold]")
    for f in files:
        if not f.exists():
            console.print(f"[red]Error: File not found: {f}[/red]")
            raise typer.Exit(1)
        if f.suffix.lower() not in {".pdf", ".txt"}:
            console.print(
                f"[red]Error: Unsupported file type '{f.suffix}' for {f.name}. "
                "Only .pdf and .txt files are accepted.[/red]"
            )
            raise typer.Exit(1)
        console.print(f"  - {f.name}")

    # --- Separate by type ---
    pdf_files = [f for f in files if f.suffix.lower() == ".pdf"]
    txt_files = [f for f in files if f.suffix.lower() == ".txt"]

    if not pdf_files and not txt_files:
        console.print("[red]Error: No .pdf or .txt files provided.[/red]")
        raise typer.Exit(1)

    # --- Determine session number ---
    effective_session = session_number if session_number is not None else 0

    # --- Run pipeline ---
    try:
        result = asyncio.run(
            _run_ingest_pipeline(
                files=files,
                session_number=effective_session,
                pdf_files=pdf_files,
                txt_files=txt_files,
            )
        )
    except _ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\nFix your configuration and try again:")
        console.print("  scribe config")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Pipeline error: {e}[/red]")
        raise typer.Exit(1)

    # --- Print summary ---
    console.print("\n[bold green]Extraction complete![/bold green]")
    console.print(f"  NPCs:         {len(result.npcs)}")
    console.print(f"  Locations:    {len(result.locations)}")
    console.print(f"  Factions:     {len(result.factions)}")
    console.print(f"  Loot items:   {len(result.loot)}")
    console.print(f"  Plot threads: {len(result.plot_threads)}")
    if result.questions:
        console.print(f"  Questions:    {len(result.questions)}")

    # --- Print recap ---
    if result.recap:
        console.print(f"\n[bold]Session Recap — {result.recap.title}[/bold]")
        console.print(result.recap.summary)


@app.command()
def init() -> None:
    """Initialise the Obsidian vault folder structure for Session Scribe."""
    try:
        settings = Settings()
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        console.print("\nCopy .env.example to .env and fill in your values:")
        console.print("  cp .env.example .env")
        raise typer.Exit(1)

    if not settings.vault_name:
        console.print(
            "[red]Error: SCRIBE_VAULT_NAME is not set.[/red]\n"
            "Set the vault name in your .env file or environment:\n"
            "  export SCRIBE_VAULT_NAME='My Campaign Vault'"
        )
        raise typer.Exit(1)

    cli = ObsidianCLI(settings.vault_name)
    vault_manager = VaultManager(cli)

    try:
        vault_manager.init_vault()
    except Exception as exc:
        console.print(f"[red]Failed to initialise vault: {exc}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold green]Vault initialised![/bold green]")
    console.print(f"  Vault name: {settings.vault_name}")
    console.print("  Created folders: Sessions, NPCs, Locations, Factions, Loot, Plot-Threads, _Agent")
    console.print("  Created seed files: Dashboard, Timeline, Open/Closed Threads, Agent Memory")
    console.print("\nYou're ready to run [bold]scribe ingest[/bold].")


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
        settings = Settings()
        console.print("[bold]Session Scribe Configuration[/bold]")
        console.print(f"  Vault path:       {settings.vault_path}")
        console.print(f"  LLM provider:     {settings.llm_provider}")
        if settings.llm_provider == "kimi":
            console.print(f"  Kimi model:       {settings.kimi_model or '(default)'}")
        else:
            console.print(f"  nano-gpt model:   {settings.nanogpt_model}")
            console.print(f"  API key:          {'***' + settings.nanogpt_api_key[-4:] if settings.nanogpt_api_key else '(not set)'}")
        console.print(f"  LM Studio URL:    {settings.lm_studio_base_url}")
        console.print(f"  Embedding model:  {settings.embedding_model}")
        console.print(f"  Log level:        {settings.log_level}")

        if not settings.vault_path.exists():
            console.print(f"\n[yellow]Warning: Vault path does not exist: {settings.vault_path}[/yellow]")
        else:
            console.print("\n[green]Vault path exists.[/green]")
    except Exception as e:
        from pydantic import ValidationError

        if isinstance(e, ValidationError):
            missing = [err["loc"][0] for err in e.errors() if err["type"] == "missing"]
            if missing:
                env_vars = [f"SCRIBE_{name.upper()}" for name in missing]
                console.print(f"[red]Configuration error: missing required setting(s): {', '.join(env_vars)}[/red]")
            else:
                console.print(f"[red]Configuration error: {e}[/red]")
        else:
            console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\nCopy .env.example to .env and fill in your values:")
        console.print("  cp .env.example .env")
        raise typer.Exit(1)


@app.command()
def stats() -> None:
    """Show LLM usage statistics and cost tracking."""
    console.print("[bold]Session Scribe Stats[/bold]")
    console.print("No usage data yet.")
