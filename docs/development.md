# Development Guide

Everything you need to set up a local environment, run tests, and contribute to
Chronicler.

---

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (package and environment management)
- Git

For the full runtime environment you'll also need the same external tools a
regular user would need — see [installation.md](installation.md) for details on
Obsidian, an LLM provider, and LM Studio.

---

## Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/ScottSucksAtProgramming/chronicler.git
cd chronicler

# 2. Create the virtualenv and install all dependencies (including dev)
uv sync --dev

# 3. Verify the CLI is wired up
uv run chronicler --help
```

For a working local config run `uv run chronicler config init` and follow the
prompts.

---

## Running Tests

The default test run covers all unit tests and excludes integration tests:

```bash
uv run pytest
```

Run a single file or directory:

```bash
uv run pytest tests/ingestion/test_source_classifier.py
```

Run integration tests (require real Obsidian + LM Studio):

```bash
uv run pytest -m integration
```

Integration tests are excluded from CI; run them locally when changing vault or
embedding code.

For unit tests that exercise `Settings`, construct the object directly rather
than relying on a real config file:

```python
settings = Settings(vault_path="/tmp/test-vault", vault_name="test")
```

---

## Linting and Formatting

Check for issues:

```bash
uv run ruff check src/ tests/
uv run black --check src/ tests/
```

Apply formatting:

```bash
uv run black src/ tests/
```

Both checks run in CI on every push. Fix any failures before opening a PR.

---

## Project Structure

See `CLAUDE.md` for the full annotated tree and module boundaries. The short
version:

| Layer | Location |
|---|---|
| CLI entry point | `src/chronicler/cli/main.py` |
| Pydantic models | `src/chronicler/models/` |
| LLM gateway | `src/chronicler/gateway/` |
| Configuration | `src/chronicler/config/settings.py` |
| Ingestion pipeline | `src/chronicler/ingestion/` |
| Extraction | `src/chronicler/extraction/` |
| Vault operations | `src/chronicler/vault/` |
| Embeddings | `src/chronicler/retrieval/` |

Dependencies point inward: domain logic never imports from infrastructure.
Files stay under roughly 300 lines. One job per module.

---

## Architecture Notes

- **Clean Architecture:** Domain logic (`models/`, `extraction/`) never
  depends on `vault/`, `gateway/`, or `retrieval/`. Infrastructure adapts to
  domain types, not the other way around.
- **Pydantic models everywhere:** No raw dicts crossing module boundaries.
  `ExtractionResult`, `ContextBundle`, and friends are the contracts.
- **Vault is source of truth:** All campaign state lives in Obsidian notes.
  The agent reads vault context before every extraction so later sessions
  benefit from earlier ones.
- **LLM Gateway handles retries:** Callers don't retry LLM calls themselves.
  `LLMGateway` handles `llm_max_retries` and `llm_timeout_seconds`.

For the full design rationale see
`docs/superpowers/specs/2026-04-02-session-scribe-design.md`.

---

## Branching and Commits

Branch from `main`. Use descriptive names:

```
feat/public-release-metadata
fix/source-classifier-anchor
docs/update-quick-start
```

Commit message prefixes:

| Prefix | When to use |
|---|---|
| `feat:` | User-facing feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `test:` | Test only |
| `refactor:` | Internal restructuring, no behavior change |
| `chore:` | Tooling, metadata, maintenance |
| `ci:` | CI/CD pipeline changes |

---

## Opening a Pull Request

Before opening a PR:

- [ ] Relevant tests pass locally (`uv run pytest`)
- [ ] Ruff and Black checks pass locally
- [ ] Branch is up to date with `main`
- [ ] PR description covers what changed, why, and how it was verified
- [ ] Follow-up work or known limitations are called out

For significant work, open an issue first so scope is aligned before
implementation starts. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full
contribution guidelines including review expectations.
