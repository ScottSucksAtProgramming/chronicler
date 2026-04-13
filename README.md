# Chronicler

[![CI](https://github.com/ScottSucksAtProgramming/chronicler/actions/workflows/ci.yml/badge.svg)](https://github.com/ScottSucksAtProgramming/chronicler/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/chronicler)](https://pypi.org/project/chronicler/)

Chronicler is a local-first CLI for turning tabletop RPG session exports into an Obsidian campaign vault. It ingests PLAUD summary PDFs and transcript text files, extracts campaign entities with an LLM, writes linked notes into your vault, builds a local retrieval index, and gives you a chat interface over your campaign history.

## What It Does

- Initializes a structured Obsidian vault for campaign notes
- Ingests session files from PLAUD exports
- Extracts NPCs, locations, factions, loot, plot threads, and a session recap
- Writes and updates campaign notes in Obsidian
- Tracks open threads and review findings
- Manages player character notes so PCs do not get mistaken for NPCs
- Builds a local ChromaDB index over your vault
- Provides a Textual chat UI for asking campaign questions

## Current Architecture

Chronicler is a Python package with a Typer CLI, Pydantic models, an LLM gateway, Obsidian vault management, extraction/retrieval modules, and a Textual-based chat app.

It currently supports:

- `kimi` via the Kimi CLI for extraction and chat
- `nanogpt` via the nano-gpt.com API
- LM Studio for local embeddings used by reindexing and chat
- Obsidian CLI for vault discovery, reading, and writing

## Prerequisites

You need the following installed before using Chronicler:

- Python 3.12+
- `uv`
- Obsidian desktop with CLI support enabled
- A local Obsidian vault for your campaign
- One LLM provider:
  - Kimi CLI
  - nano-gpt.com API key
- LM Studio with an embedding model loaded if you want `reindex` or `chat`

Important current constraint:

- The Obsidian CLI wrapper currently defaults to the macOS app binary at `/Applications/Obsidian.app/Contents/MacOS/obsidian`

## Installation

Clone the repo and install dependencies:

```bash
git clone <your-remote-url> chronicler
cd chronicler
uv sync
```

Verify the CLI is available:

```bash
uv run chronicler --help
```

## Global CLI Install

If you want `chronicler` available as a normal shell command from anywhere on your machine, install it as a global uv tool from the repo root:

```bash
uv tool install .
```

After that, you can run:

```bash
chronicler --help
```

When you make local changes and want to refresh the installed command, run:

```bash
uv tool uninstall chronicler
uv tool install .
```

To remove the global command later:

```bash
uv tool uninstall chronicler
```

## Configuration

Initialize the persistent config file with the built-in wizard:

```bash
uv run chronicler config init
```

By default Chronicler stores `config.toml` in the standard user config directory for your OS:

- macOS: `~/Library/Application Support/chronicler/config.toml`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/chronicler/config.toml`
- Windows: `%APPDATA%\chronicler\config.toml`

The wizard collects the required settings for you and can also capture optional overrides for LM Studio, embeddings, and logging.

Inspect the active configuration at any time:

```bash
uv run chronicler config show
```

Bare `uv run chronicler config` still works and behaves the same as `config show`.

Environment variables prefixed with `CHRONICLER_` still override the config file for CI, scripts, and temporary overrides. `.env.example` remains in the repo as a reference document for those environment variable names.

## Getting Started

Recommended first-run flow:

1. Create or choose an Obsidian vault for your campaign.
2. Run `uv run chronicler config init`.
3. Run `uv run chronicler init`.
4. Add your party members with `chronicler party add`.
5. Ingest one session with `chronicler ingest`.
6. Run `chronicler review` and `chronicler ask`.
7. Open `chronicler chat` after the vault has been indexed.

### 1. Initialize the Vault

```bash
uv run chronicler init
```

This seeds the vault with:

- `Sessions/`
- `Party/`
- `NPCs/`
- `Locations/`
- `Factions/`
- `Loot/`
- `Plot-Threads/`
- `_Agent/`
- `_Dashboard.md`
- `Timeline.md`
- review and memory files under `_Agent/`

### 2. Add Player Characters

Add your PCs before ingestion so extraction has party context:

```bash
uv run chronicler party add --player "Alice" --character "Nyra" --class "Wizard"
uv run chronicler party add --player "Ben" --character "Thorn" --class "Ranger"
uv run chronicler party list
```

Remove a PC note if needed:

```bash
uv run chronicler party remove --character "Nyra"
```

### 3. Ingest a Session

The safest workflow is to pass an explicit session number:

```bash
uv run chronicler ingest --session 22 /path/to/session-22-summary.pdf /path/to/session-22-transcript.txt
```

You can ingest only a PDF or only a transcript, but the best results come from supplying both.

During ingest, Chronicler:

- parses the PDF and transcript
- loads vault context
- filters banter
- extracts structured entities
- writes notes to the vault
- records quality metrics
- attempts an automatic reindex if LM Studio is available

### 4. Review Open Questions

Run a vault review:

```bash
uv run chronicler review
```

This prints findings and appends them to `_Agent/Review-Log.md`.

Then review pending questions:

```bash
uv run chronicler ask
```

If you run it in an interactive terminal, you can answer questions inline and append responses to the corresponding note under `_Agent/Questions/`.

### 5. Rebuild Retrieval Index

If LM Studio is running, you can rebuild the vector index manually:

```bash
uv run chronicler reindex
```

This stores local index data under `.chronicler/` inside your vault path.

### 6. Ask Questions In Chat

Once the index exists:

```bash
uv run chronicler chat
```

Inside chat:

- Ask free-form campaign questions
- Use `/help` for chat commands
- Use `/quit` to exit

## Command Reference

### `chronicler init`

Initializes the Obsidian vault structure and seed notes.

### `chronicler party list`

Shows configured player characters.

### `chronicler party add --player NAME --character NAME [--class CLASS]`

Creates or updates a player character note in `Party/`.

### `chronicler party remove --character NAME`

Deletes a player character note from `Party/`.

### `chronicler ingest [--session N] FILE...`

Processes one or more `.pdf` and `.txt` session files.

### `chronicler review`

Runs consistency checks over the vault and logs findings.

### `chronicler ask`

Displays pending agent questions and, in a TTY session, allows inline answers.

### `chronicler reindex`

Rebuilds the embedding index used by retrieval and chat.

### `chronicler chat`

Launches the interactive campaign Q&A TUI.

### `chronicler config show`

Prints active configuration and validates the vault path.

### `chronicler config init`

Runs the interactive wizard that writes `config.toml`.

### `chronicler stats`

Shows extraction quality metrics accumulated across processed sessions.

## Typical Workflow

For backlog processing:

1. Add your party once.
2. Ingest a session with `--session`.
3. Review the written notes in Obsidian.
4. Run `review`.
5. Answer pending `ask` questions.
6. Re-ingest or continue to the next session.

For active campaign use:

1. Ingest the newest session after play.
2. Review open threads in Obsidian.
3. Use `chat` before the next game to refresh your memory.

## Troubleshooting

### `CHRONICLER_VAULT_NAME is not set`

Run `chronicler config init` and make sure the saved `vault_name` matches the vault name Obsidian CLI uses, not just the filesystem folder name.

### Obsidian CLI errors

Make sure:

- Obsidian desktop is installed
- the app is running
- the configured vault exists
- the `vault_name` in `config.toml` matches the one shown in Obsidian

### LM Studio connection errors

`chat` and `reindex` require LM Studio to be running with an embedding model loaded. Verify the base URL and model name in `config.toml`.

### nano-gpt provider errors

If `CHRONICLER_LLM_PROVIDER=nanogpt`, you must also set `CHRONICLER_NANOGPT_API_KEY`.

### Kimi CLI not found

Install the Kimi CLI and ensure the `kimi` command is on your `PATH`.

## Repository Guide

- Source code lives under `src/chronicler/`
- Tests live under `tests/`
- Historical discovery and planning docs live under `docs/`
- Architecture overview: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- A quick file map lives in `INDEX.md`

## Project Status

This repo is usable now for local vault initialization, ingestion, review, indexing, and chat. It is still an actively evolving tool, so expect implementation-oriented docs and some rough edges around environment assumptions.
