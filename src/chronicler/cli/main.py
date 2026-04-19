"""Chronicler CLI — entry point for all user interaction."""

import asyncio
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from chronicler.config.files import (
    get_field_sources,
    load_config_file,
    write_config_file,
)
from chronicler.config.paths import get_config_path
from chronicler.config.settings import Settings
from chronicler.extraction.source_extractor import extract_source_document
from chronicler.gateway.llm_gateway import LLMGateway
from chronicler.ingestion import (
    classify_source_document,
    is_ambiguous,
    parse_source_document,
)
from chronicler.models import DocumentType, SourceClassification
from chronicler.models.context import PlayerCharacter
from chronicler.models.extraction import ExtractionResult, KnowledgeIngestResult
from chronicler.reviewer import review_vault
from chronicler.vault.improver import improve_vault
from chronicler.vault.metrics import QualityMetrics, SessionMetric
from chronicler.vault.obsidian_cli import ObsidianCLI
from chronicler.vault.source_archive import archive_source_document
from chronicler.vault.vault_manager import VaultManager

app = typer.Typer(
    name="chronicler",
    help="Chronicler — AI-powered tabletop campaign note management.",
    no_args_is_help=True,
)
party_app = typer.Typer(help="Manage player characters.")
config_app = typer.Typer(help="Inspect and manage configuration.")
app.add_typer(party_app, name="party")
app.add_typer(config_app, name="config")
console = Console()
_SESSION_FILE_SUFFIXES = {".pdf", ".txt"}
_SOURCE_FILE_SUFFIXES = {".md", ".txt", ".pdf"}


class _ConfigError(Exception):
    """Raised when Settings cannot be loaded."""


def version_callback(value: bool) -> None:
    if value:
        console.print("chronicler v0.1.0")
        raise typer.Exit()


def _load_vault_manager() -> VaultManager:
    """Create a vault manager from the current settings."""
    try:
        settings = Settings()
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        raise typer.Exit(1) from exc

    if not settings.vault_name:
        console.print("[red]Error: CHRONICLER_VAULT_NAME is not set.[/red]")
        raise typer.Exit(1)

    cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)
    return VaultManager(cli)


def _confirm_ambiguous_source(file_path: Path) -> SourceClassification:
    console.print(f"[yellow]Could not confidently classify {file_path.name}.[/yellow]")
    selected = typer.prompt(
        "How should this source be treated? "
        "(session_transcript, session_summary, session_support, legacy_note, campaign_background)",
        default="legacy_note",
    )
    return SourceClassification(
        document_type=DocumentType(selected),
        confidence=1.0,
    )


def _metrics_path(settings: Settings) -> Path:
    """Return the metrics storage path inside the configured vault."""
    return settings.vault_path / ".chronicler" / "metrics.json"


def _format_source_annotation(field_sources: dict[str, str], field_name: str) -> str:
    source = field_sources[field_name]
    if source == "env":
        return " (from env)"
    if source == "default":
        return " (default)"
    return ""


def _mask_api_key(api_key: str) -> str:
    if not api_key:
        return "(not set)"

    return f"***{api_key[-4:]}"


def _prompt_existing_path(prompt: str, default: str | None = None) -> Path:
    while True:
        raw = typer.prompt(prompt, default=default)
        value = Path(raw).expanduser()
        if value.exists():
            return value
        console.print(f"[red]Path does not exist: {value}[/red]")


def _prompt_provider(default: str = "kimi") -> str:
    valid_providers = {"kimi", "nanogpt"}
    while True:
        provider = typer.prompt("LLM provider", default=default).strip().lower()
        if provider in valid_providers:
            return provider
        console.print("[red]Please enter either 'kimi' or 'nanogpt'.[/red]")


def _prompt_optional_value(prompt: str, default: str) -> tuple[str, bool]:
    value = typer.prompt(prompt, default=default)
    return value, value != default


def _print_vault_name_error() -> None:
    console.print(
        "[red]Error: CHRONICLER_VAULT_NAME is not set.[/red]\n"
        "Run [bold]chronicler config init[/bold] to create or refresh your config file,\n"
        "or set `vault_name` manually in your TOML config."
    )


def _record_session_metric(
    settings: Settings,
    cli: ObsidianCLI,
    result: ExtractionResult,
) -> None:
    """Persist quality metrics for a processed session."""
    report = review_vault(cli)
    metrics = QualityMetrics(_metrics_path(settings))
    metrics.add(
        SessionMetric(
            session_number=result.session_number,
            npc_count=len(result.npcs),
            location_count=len(result.locations),
            faction_count=len(result.factions),
            thread_count=len(result.plot_threads),
            question_count=len(result.questions),
            quality_score=result.quality_score.average if result.quality_score else 0.0,
            reviewer_findings=report.total_findings,
        )
    )


async def _auto_reindex_vault(settings: Settings, cli: ObsidianCLI) -> int | None:
    """Reindex the vault after ingest when embeddings are available."""
    from chronicler.retrieval.embeddings import EmbeddingClient
    from chronicler.retrieval.indexer import VaultIndexer
    import chromadb

    embed_client = EmbeddingClient(
        settings.lm_studio_base_url, settings.embedding_model
    )
    if not embed_client.health_check():
        return None

    chroma_client = chromadb.PersistentClient(
        path=str(settings.vault_path / ".chronicler" / "chromadb")
    )
    collection = chroma_client.get_or_create_collection("vault_notes")
    indexer = VaultIndexer(cli, embed_client, collection)
    return await indexer.index_vault(vault_path=str(settings.vault_path))


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """Chronicler — AI-powered tabletop campaign note management."""


async def _run_ingest_pipeline(
    files: list[Path],
    session_number: int,
    pdf_files: list[Path],
    txt_files: list[Path],
) -> "ExtractionResult":
    """Async helper that runs the full ingestion and extraction pipeline."""
    from chronicler.extraction.extractor import extract_session
    from chronicler.gateway.llm_gateway import LLMGateway
    from chronicler.ingestion.normalizer import normalize_session
    from chronicler.ingestion.pdf_parser import parse_plaud_pdf
    from chronicler.ingestion.transcript_parser import parse_transcript
    from chronicler.models.context import ContextBundle

    try:
        settings = Settings()
    except Exception as exc:
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            missing = [
                err["loc"][0] for err in exc.errors() if err["type"] == "missing"
            ]
            if missing:
                env_vars = [f"CHRONICLER_{name.upper()}" for name in missing]
                raise _ConfigError(
                    f"missing required setting(s): {', '.join(env_vars)}"
                ) from exc
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
            cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)
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
                _record_session_metric(settings, cli, result)
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

                console.print("[cyan]Updating search index...[/cyan]")
                chunk_count = await _auto_reindex_vault(settings, cli)
                if chunk_count is None:
                    console.print(
                        "[dim]LM Studio not running — skipping search index update[/dim]"
                    )
                else:
                    console.print(
                        f"[green]Search index updated:[/green] {chunk_count} chunks"
                    )
            except Exception as exc:
                console.print(
                    f"[yellow]Warning: Could not write to vault: {exc}[/yellow]"
                )

        return result
    finally:
        await gateway.close()


async def _run_source_ingest_pipeline(
    files: list[Path],
    session_number: int | None,
) -> "KnowledgeIngestResult":
    """Async helper that extracts knowledge from general source documents."""
    from chronicler.models.context import ContextBundle

    try:
        settings = Settings()
    except Exception as exc:
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            missing = [
                err["loc"][0] for err in exc.errors() if err["type"] == "missing"
            ]
            if missing:
                env_vars = [f"CHRONICLER_{name.upper()}" for name in missing]
                raise _ConfigError(
                    f"missing required setting(s): {', '.join(env_vars)}"
                ) from exc
        raise _ConfigError(str(exc)) from exc

    gateway = LLMGateway(settings)

    try:
        document = parse_source_document(files[0])
        classification = classify_source_document(document, session_number)
        document.classification = classification
        vault_manager = None

        if settings.vault_name:
            cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)
            vault_manager = VaultManager(cli)
            try:
                context = vault_manager.get_context_bundle(session_number or 0)
            except Exception:
                context = ContextBundle(session_number=session_number or 0)
        else:
            context = ContextBundle(session_number=session_number or 0)

        model = (
            settings.kimi_model or "kimi-default"
            if settings.llm_provider == "kimi"
            else settings.nanogpt_model
        )

        result = await extract_source_document(
            document=document,
            context=context,
            gateway=gateway,
            model=model,
        )
        archive_vault_path = settings.vault_path
        if vault_manager is not None:
            resolved_path = cli.get_vault_path()
            if resolved_path is not None:
                archive_vault_path = resolved_path
        archive_source_document(archive_vault_path, document)
        if vault_manager is not None:
            vault_manager.write_source_ingest_result(result)
        return result
    finally:
        await gateway.close()


@app.command()
def ingest(
    files: Annotated[
        list[Path],
        typer.Argument(help="Source files to ingest. Accepts .pdf, .txt, and .md."),
    ],
    session_number: Annotated[
        Optional[int],
        typer.Option(
            "--session", "-s", help="Session number. Auto-detected if not provided."
        ),
    ] = None,
) -> None:
    """Ingest session recordings and source materials into the campaign vault."""
    # --- Validate files ---
    console.print(f"[bold]Ingesting {len(files)} file(s)...[/bold]")
    for f in files:
        if not f.exists():
            console.print(f"[red]Error: File not found: {f}[/red]")
            raise typer.Exit(1)
        if f.suffix.lower() not in (_SESSION_FILE_SUFFIXES | _SOURCE_FILE_SUFFIXES):
            console.print(
                f"[red]Error: Unsupported file type '{f.suffix}' for {f.name}. "
                "Supported types currently include .pdf, .txt, and .md.[/red]"
            )
            raise typer.Exit(1)
        console.print(f"  - {f.name}")

    # --- Separate by type ---
    pdf_files = [f for f in files if f.suffix.lower() == ".pdf"]
    txt_files = [f for f in files if f.suffix.lower() == ".txt"]
    source_files = [f for f in files if f.suffix.lower() in _SOURCE_FILE_SUFFIXES]

    if not pdf_files and not txt_files and not source_files:
        console.print("[red]Error: No supported source files provided.[/red]")
        raise typer.Exit(1)

    # --- Determine session number ---
    effective_session = session_number if session_number is not None else 0

    # --- Smart route a single file by classified intent ---
    if len(files) == 1:
        document = parse_source_document(files[0])
        classification = classify_source_document(document, session_number)
        if is_ambiguous(classification):
            classification = _confirm_ambiguous_source(files[0])

        if classification.document_type in {
            DocumentType.LEGACY_NOTE,
            DocumentType.CAMPAIGN_BACKGROUND,
            DocumentType.MAP_IMAGE,
            DocumentType.TABLE_REFERENCE,
        }:
            try:
                source_result = asyncio.run(
                    _run_source_ingest_pipeline(files, session_number)
                )
            except _ConfigError as e:
                console.print(f"[red]Configuration error: {e}[/red]")
                console.print("\nFix your configuration and try again:")
                console.print("  chronicler config")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]Pipeline error: {e}[/red]")
                raise typer.Exit(1)

            console.print("\n[bold green]Knowledge ingest complete![/bold green]")
            console.print(f"  NPCs:         {len(source_result.npcs)}")
            console.print(f"  Locations:    {len(source_result.locations)}")
            console.print(f"  Factions:     {len(source_result.factions)}")
            console.print(f"  Loot items:   {len(source_result.loot)}")
            console.print(f"  Plot threads: {len(source_result.plot_threads)}")
            if source_result.questions:
                console.print(f"  Questions:    {len(source_result.questions)}")
            if source_result.recap:
                console.print(
                    f"\n[bold]Anchored Recap — {source_result.recap.title}[/bold]"
                )
                console.print(source_result.recap.summary)
            return

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
        console.print("  chronicler config")
        raise typer.Exit(1)
    except Exception as e:
        message = str(e)
        if "high-risk content" in message or "explicit off-topic banter" in message:
            console.print(f"[red]Pipeline error: {message}[/red]")
            console.print(
                "\nThe transcript likely included explicit real-world banter that triggered provider moderation."
            )
            console.print("Try one of these:")
            console.print("  1. Provide the PDF summary alongside the transcript")
            console.print(
                "  2. Trim obvious off-topic explicit banter from the transcript"
            )
            console.print(
                "  3. Retry after confirming the transcript was segmented correctly"
            )
        else:
            console.print(f"[red]Pipeline error: {message}[/red]")
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
    """Initialise the Obsidian vault folder structure for Chronicler."""
    try:
        settings = Settings()
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        console.print("\nRun the config wizard to create your settings file:")
        console.print("  chronicler config init")
        raise typer.Exit(1)

    if not settings.vault_name:
        _print_vault_name_error()
        raise typer.Exit(1)

    cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)
    vault_manager = VaultManager(cli)

    try:
        vault_manager.init_vault()
    except Exception as exc:
        console.print(f"[red]Failed to initialise vault: {exc}[/red]")
        raise typer.Exit(1)

    console.print("[bold green]Vault initialised![/bold green]")
    console.print(f"  Vault name: {settings.vault_name}")
    console.print(
        "  Created folders: Sessions, NPCs, Locations, Factions, Loot, Plot-Threads, _Agent"
    )
    console.print(
        "  Created seed files: Dashboard, Timeline, Open/Closed Threads, Agent Memory"
    )
    console.print("\nYou're ready to run [bold]chronicler ingest[/bold].")


@party_app.command("list")
def party_list() -> None:
    """List configured player characters."""
    vault_manager = _load_vault_manager()
    pcs = vault_manager.read_player_characters()

    if not pcs:
        console.print("No player characters configured yet.")
        return

    console.print("[bold]Player Characters[/bold]")
    for pc in pcs:
        details = f"{pc.player_name} -> {pc.character_name}"
        if pc.character_class:
            details += f" ({pc.character_class})"
        console.print(details)


@party_app.command("add")
def party_add(
    player: Annotated[str, typer.Option("--player", help="Player name.")],
    character: Annotated[str, typer.Option("--character", help="Character name.")],
    character_class: Annotated[
        Optional[str],
        typer.Option("--class", help="Character class."),
    ] = None,
) -> None:
    """Add a player character note to the party."""
    vault_manager = _load_vault_manager()
    vault_manager.write_pc(
        PlayerCharacter(
            player_name=player,
            character_name=character,
            character_class=character_class,
        )
    )
    console.print(f"[green]Added player character:[/green] {character}")


@party_app.command("remove")
def party_remove(
    character: Annotated[str, typer.Option("--character", help="Character name.")],
) -> None:
    """Remove a player character note from the party."""
    vault_manager = _load_vault_manager()
    vault_manager.remove_pc(character)
    console.print(f"[green]Removed player character:[/green] {character}")


@app.command()
def chat() -> None:
    """Open interactive campaign Q&A chat."""
    try:
        settings = Settings()
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        raise typer.Exit(1)

    if not settings.vault_name:
        _print_vault_name_error()
        raise typer.Exit(1)

    from chronicler.retrieval.embeddings import EmbeddingClient

    embed_client = EmbeddingClient(
        settings.lm_studio_base_url, settings.embedding_model
    )
    if not embed_client.health_check():
        console.print(
            "[red]Error: Cannot connect to LM Studio at "
            f"{settings.lm_studio_base_url}.[/red]\n"
            "Make sure LM Studio is running with an embedding model loaded."
        )
        raise typer.Exit(1)

    import chromadb

    chroma_client = chromadb.PersistentClient(
        path=str(settings.vault_path / ".chronicler" / "chromadb")
    )
    collection = chroma_client.get_or_create_collection("vault_notes")

    if collection.count() == 0:
        console.print(
            "[yellow]Warning: The vault index is empty. "
            "Run [bold]chronicler reindex[/bold] first to index your notes.[/yellow]"
        )
        raise typer.Exit(1)

    from chronicler.chat.app import ChatApp
    from chronicler.gateway.llm_gateway import LLMGateway
    from chronicler.retrieval.retrieval import RetrievalLayer

    layer = RetrievalLayer(collection, embed_client)
    gateway = LLMGateway(settings)
    cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)
    vault_manager = VaultManager(cli)

    model = (
        settings.kimi_model or "kimi-default"
        if settings.llm_provider == "kimi"
        else settings.nanogpt_model
    )

    ChatApp(
        retrieval=layer,
        gateway=gateway,
        model=model,
        vault_manager=vault_manager,
    ).run()

    asyncio.run(gateway.close())
    asyncio.run(embed_client.close())


@app.command()
def review() -> None:
    """Run a quality review pass over the vault."""
    try:
        settings = Settings()
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        raise typer.Exit(1)

    if not settings.vault_name:
        console.print("[red]Error: CHRONICLER_VAULT_NAME is not set.[/red]")
        raise typer.Exit(1)

    cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)
    report = review_vault(cli)

    # Print each finding with severity-based colouring
    for finding in report.findings:
        if finding.severity.value == "error":
            style = "red"
        elif finding.severity.value == "warning":
            style = "yellow"
        else:
            style = "dim"

        file_str = f" [{finding.file}]" if finding.file else ""
        console.print(
            f"[{style}]{finding.severity.value.upper()}{file_str}: {finding.detail}[/{style}]"
        )

    # Summary
    console.print(
        f"\nReview complete: {report.error_count} errors, "
        f"{report.warning_count} warnings, {report.info_count} info"
    )

    # Write findings to _Agent/Review-Log.md
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_lines = [f"\n\n## Review — {timestamp}\n"]
    if report.findings:
        for f in report.findings:
            log_lines.append(f"- **{f.severity.value.upper()}** {f.file}: {f.detail}")
    else:
        log_lines.append("- No issues found.")
    log_lines.append(
        f"\n**Summary:** {report.error_count} errors, "
        f"{report.warning_count} warnings, {report.info_count} info\n"
    )

    try:
        cli.append("_Agent/Review-Log.md", "\n".join(log_lines))
    except Exception:
        # If the file doesn't exist yet, create it
        try:
            cli.create("_Agent/Review-Log.md", "# Review Log\n" + "\n".join(log_lines))
        except Exception as exc:
            console.print(
                f"[yellow]Warning: Could not write review log: {exc}[/yellow]"
            )


@app.command()
def improve() -> None:
    """Run deterministic vault maintenance and queue questions for ambiguities."""
    try:
        settings = Settings()
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        raise typer.Exit(1)

    if not settings.vault_name:
        console.print("[red]Error: CHRONICLER_VAULT_NAME is not set.[/red]")
        raise typer.Exit(1)

    cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)
    report = improve_vault(cli)

    console.print(
        f"[bold green]Improvement complete[/bold green]: "
        f"{report.changed_count} note(s) updated, {report.question_count} question(s) created"
    )
    if report.changed_files:
        console.print("Updated:")
        for path in report.changed_files:
            console.print(f"  - {path}")
    if report.question_files:
        console.print("Questions:")
        for path in report.question_files:
            console.print(f"  - {path}")


@app.command()
def ask() -> None:
    """Review and answer the agent's pending questions."""
    try:
        settings = Settings()
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        raise typer.Exit(1)

    if not settings.vault_name:
        console.print("[red]Error: CHRONICLER_VAULT_NAME is not set.[/red]")
        raise typer.Exit(1)

    cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)

    # List question files, excluding the answered/ subfolder
    all_questions = cli.find_notes_in_folder("_Agent/Questions/")
    questions = [
        q for q in all_questions if not q.startswith("_Agent/Questions/answered/")
    ]

    if not questions:
        console.print("No pending questions.")
        raise typer.Exit()

    interactive = sys.stdin.isatty()
    answered_count = 0

    for q_path in questions:
        try:
            content = cli.read(q_path)
        except Exception:
            console.print(f"[yellow]Could not read {q_path}[/yellow]")
            continue

        # Parse title from # heading
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else Path(q_path).stem

        # Parse context from ## Context section
        context_match = re.search(
            r"^##\s+Context\s*\n(.*?)(?=\n##|\Z)", content, re.MULTILINE | re.DOTALL
        )
        context_text = context_match.group(1).strip() if context_match else ""

        # Parse priority and source_session from frontmatter
        priority = ""
        source_session = ""
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            p_match = re.search(r"priority:\s*(.+)", fm)
            if p_match:
                priority = p_match.group(1).strip()
            s_match = re.search(r"source_session:\s*(.+)", fm)
            if s_match:
                source_session = s_match.group(1).strip()

        # Display
        console.print(f"\n[bold]{title}[/bold]")
        if context_text:
            console.print(f"[dim]{context_text}[/dim]")
        meta_parts = []
        if priority:
            meta_parts.append(f"Priority: {priority}")
        if source_session:
            meta_parts.append(f"Session: {source_session}")
        if meta_parts:
            console.print(f"[dim]({', '.join(meta_parts)})[/dim]")

        if not interactive:
            continue

        answer = input("Your answer (Enter to skip): ")
        if answer.strip():
            try:
                cli.append(q_path, f"\n\n## Answer\n\n{answer.strip()}")
                answered_count += 1
                console.print("[green]Answer saved.[/green]")
            except Exception as exc:
                console.print(f"[yellow]Could not save answer: {exc}[/yellow]")

    console.print(f"\nAnswered {answered_count} of {len(questions)} questions.")


@app.command()
def reindex() -> None:
    """Rebuild the vector store index from current vault contents."""
    try:
        settings = Settings()
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        raise typer.Exit(1)

    if not settings.vault_name:
        _print_vault_name_error()
        raise typer.Exit(1)

    from chronicler.retrieval.embeddings import EmbeddingClient
    from chronicler.retrieval.indexer import VaultIndexer

    cli = ObsidianCLI(settings.vault_name, vault_path=settings.vault_path)
    embed_client = EmbeddingClient(
        settings.lm_studio_base_url, settings.embedding_model
    )

    if not embed_client.health_check():
        console.print(
            "[red]Error: Cannot connect to LM Studio at "
            f"{settings.lm_studio_base_url}.[/red]\n"
            "Make sure LM Studio is running with an embedding model loaded."
        )
        raise typer.Exit(1)

    import chromadb

    chroma_client = chromadb.PersistentClient(
        path=str(settings.vault_path / ".chronicler" / "chromadb")
    )
    collection = chroma_client.get_or_create_collection("vault_notes")

    indexer = VaultIndexer(cli, embed_client, collection)

    console.print("[cyan]Indexing vault notes...[/cyan]")
    chunk_count = asyncio.run(indexer.index_vault(vault_path=str(settings.vault_path)))
    console.print(f"[green]Indexing complete:[/green] {chunk_count} chunks indexed.")


@config_app.callback(invoke_without_command=True)
def config(ctx: typer.Context) -> None:
    """Inspect and manage Chronicler configuration."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(config_show)


@config_app.command("show")
def config_show() -> None:
    """Show current configuration and verify setup."""
    try:
        settings = Settings()
        field_sources = get_field_sources()
        console.print("[bold]Chronicler Configuration[/bold]")
        console.print(
            "  Vault path:       "
            f"{settings.vault_path}{_format_source_annotation(field_sources, 'vault_path')}"
        )
        console.print(
            "  LLM provider:     "
            f"{settings.llm_provider}{_format_source_annotation(field_sources, 'llm_provider')}"
        )
        if settings.llm_provider == "kimi":
            kimi_model = settings.kimi_model or "(default)"
            kimi_annotation = (
                ""
                if not settings.kimi_model and field_sources["kimi_model"] == "default"
                else _format_source_annotation(field_sources, "kimi_model")
            )
            console.print(f"  Kimi model:       {kimi_model}{kimi_annotation}")
        else:
            console.print(
                "  nano-gpt model:   "
                f"{settings.nanogpt_model}"
                f"{_format_source_annotation(field_sources, 'nanogpt_model')}"
            )
            console.print(
                "  API key:          "
                f"{_mask_api_key(settings.nanogpt_api_key)}"
                f"{_format_source_annotation(field_sources, 'nanogpt_api_key')}"
            )
        console.print(
            "  LM Studio URL:    "
            f"{settings.lm_studio_base_url}"
            f"{_format_source_annotation(field_sources, 'lm_studio_base_url')}"
        )
        console.print(
            "  Embedding model:  "
            f"{settings.embedding_model}"
            f"{_format_source_annotation(field_sources, 'embedding_model')}"
        )
        console.print(
            "  Log level:        "
            f"{settings.log_level}{_format_source_annotation(field_sources, 'log_level')}"
        )

        if not settings.vault_path.exists():
            console.print(
                f"\n[yellow]Warning: Vault path does not exist: {settings.vault_path}[/yellow]"
            )
        else:
            console.print("\n[green]Vault path exists.[/green]")
    except Exception as e:
        from pydantic import ValidationError

        if isinstance(e, ValidationError):
            missing = [err["loc"][0] for err in e.errors() if err["type"] == "missing"]
            if missing:
                env_vars = [f"CHRONICLER_{name.upper()}" for name in missing]
                console.print(
                    f"[red]Configuration error: missing required setting(s): {', '.join(env_vars)}[/red]"
                )
            else:
                console.print(f"[red]Configuration error: {e}[/red]")
        else:
            console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\nRun the config wizard to create your settings file:")
        console.print("  chronicler config init")
        raise typer.Exit(1)


@config_app.command("init")
def config_init() -> None:
    """Create or update the persistent config file via an interactive wizard."""
    config_path = get_config_path()
    existing = load_config_file()

    if existing:
        console.print(f"Updating existing config: [bold]{config_path}[/bold]")
        console.print("Press Enter to keep each current value.\n")
    else:
        console.print(f"Creating new config at: [bold]{config_path}[/bold]\n")

    existing_vault_path = str(existing.get("vault_path", "")) or None
    vault_path = _prompt_existing_path("Vault path", default=existing_vault_path)

    existing_vault_name = str(existing.get("vault_name", "")) or vault_path.name
    vault_name = typer.prompt("Vault name", default=existing_vault_name).strip()

    existing_provider = str(existing.get("llm_provider", "kimi"))
    llm_provider = _prompt_provider(default=existing_provider)

    config_values: dict[str, object] = {
        "vault_path": str(vault_path),
        "vault_name": vault_name,
        "llm_provider": llm_provider,
    }

    nanogpt_model_default = str(
        existing.get("nanogpt_model", Settings.model_fields["nanogpt_model"].default)
    )
    lm_studio_base_url_default = str(
        existing.get(
            "lm_studio_base_url", Settings.model_fields["lm_studio_base_url"].default
        )
    )
    embedding_model_default = str(
        existing.get(
            "embedding_model", Settings.model_fields["embedding_model"].default
        )
    )
    log_level_default = str(
        existing.get("log_level", Settings.model_fields["log_level"].default)
    )

    if llm_provider == "nanogpt":
        existing_key = str(existing.get("nanogpt_api_key", ""))
        key_hint = f" [{_mask_api_key(existing_key)}]" if existing_key else ""
        new_key = typer.prompt(
            f"nano-gpt API key{key_hint}",
            default=existing_key,
            hide_input=True,
        ).strip()
        config_values["nanogpt_api_key"] = new_key
        selected_model, should_write_model = _prompt_optional_value(
            "nano-gpt model",
            nanogpt_model_default,
        )
        if should_write_model:
            config_values["nanogpt_model"] = selected_model
    else:
        if shutil.which("kimi") is None:
            console.print(
                "[yellow]Warning: kimi was not found on PATH. "
                "You can still save the config and install it later.[/yellow]"
            )

    selected_base_url, should_write_base_url = _prompt_optional_value(
        "LM Studio base URL",
        lm_studio_base_url_default,
    )
    if should_write_base_url:
        config_values["lm_studio_base_url"] = selected_base_url

    selected_embedding_model, should_write_embedding_model = _prompt_optional_value(
        "Embedding model",
        embedding_model_default,
    )
    if should_write_embedding_model:
        config_values["embedding_model"] = selected_embedding_model

    selected_log_level, should_write_log_level = _prompt_optional_value(
        "Log level",
        log_level_default,
    )
    if should_write_log_level:
        config_values["log_level"] = selected_log_level

    console.print("\n[bold]Configuration Summary[/bold]")
    console.print(f"  Config path:      {config_path}")
    console.print(f"  Vault path:       {vault_path}")
    console.print(f"  Vault name:       {vault_name}")
    console.print(f"  LLM provider:     {llm_provider}")
    if llm_provider == "nanogpt":
        console.print(
            f"  nano-gpt model:   {config_values.get('nanogpt_model', nanogpt_model_default)}"
        )
        console.print(
            f"  API key:          {_mask_api_key(str(config_values['nanogpt_api_key']))}"
        )
    else:
        console.print("  Kimi model:       (default)")
    console.print(
        f"  LM Studio URL:    {config_values.get('lm_studio_base_url', lm_studio_base_url_default)}"
    )
    console.print(
        "  Embedding model:  "
        f"{config_values.get('embedding_model', embedding_model_default)}"
    )
    console.print(
        f"  Log level:        {config_values.get('log_level', log_level_default)}"
    )

    if not typer.confirm("Write this configuration?", default=True):
        console.print("Aborted.")
        raise typer.Exit()

    write_config_file(config_values)
    console.print(f"[green]Config saved to:[/green] {config_path}", soft_wrap=True)


@app.command()
def stats() -> None:
    """Show session quality metrics and extraction trends."""
    try:
        settings = Settings()
    except Exception:
        console.print("[bold]Chronicler Stats[/bold]")
        console.print("No quality metrics yet.")
        return

    console.print("[bold]Chronicler Stats[/bold]")
    metrics = QualityMetrics(_metrics_path(settings))
    summary = metrics.summary()

    if summary["sessions_processed"] == 0:
        console.print("No quality metrics yet.")
        return

    console.print(f"Sessions processed: {summary['sessions_processed']}")
    console.print(f"Average quality:    {summary['avg_quality']:.2f}")
    console.print(f"Total NPCs:         {summary['total_npcs']}")
    console.print(f"Total locations:    {summary['total_locations']}")
    console.print(f"Findings trend:     {summary['findings_trend']}")
