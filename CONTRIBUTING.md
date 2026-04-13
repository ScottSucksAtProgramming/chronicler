# Contributing to Chronicler

Thanks for your interest in contributing to Chronicler.

## Before You Start

- Use the issue tracker for bug reports and feature requests: <https://github.com/ScottSucksAtProgramming/chronicler/issues>
- Open an issue before starting significant feature work so scope and approach are aligned before implementation starts.
- Keep changes focused. Small, reviewable pull requests move faster than broad refactors.

## Development Setup

Chronicler targets Python 3.12 and uses `uv` for environment and dependency management.

1. Install Python 3.12 and `uv`.
2. Clone the repository.
3. Create the local environment and install project dependencies:

```bash
uv sync --dev
```

4. Copy `.env.example` to `.env` and fill in the values for your machine.
5. Install and configure the local tools your workflow needs:
   - Obsidian desktop with CLI support enabled
   - One LLM provider: Kimi CLI or a nano-gpt.com API key
   - LM Studio with an embedding model loaded if you need `reindex` or `chat`

Useful local commands:

```bash
uv run chronicler --help
uv run chronicler config
uv run pytest
uv run ruff check src/ tests/
uv run black --check src/ tests/
```

## Code Style

- Format Python code with Black.
- Lint Python code with ruff.
- Add type hints to all new or changed code.
- Keep files focused and under roughly 300 lines when practical.
- Follow the existing module boundaries and dependency direction in the project docs and `CLAUDE.md`.
- Prefer small, explicit changes over broad refactors.

To check formatting and linting locally:

```bash
uv run ruff check src/ tests/
uv run black --check src/ tests/
```

To apply formatting:

```bash
uv run black src/ tests/
```

## Testing Requirements

- Use TDD for new behavior and bug fixes where practical: write or update a failing test first, then implement the change.
- Every new behavior should have unit-test coverage.
- Integration tests must be marked with `@pytest.mark.integration`.
- Do not rely on integration tests for routine validation; the default test run excludes them.
- Run the relevant focused tests for your change, then run the unit suite before opening a PR.

Standard test commands:

```bash
uv run pytest
uv run python -m pytest tests/path/to/test_file.py
uv run pytest -m integration
```

## Branches and Pull Requests

- Branch from `main`.
- Use descriptive branch names such as `feat/public-release-metadata` or `fix/source-classifier-anchor`.
- For significant work, start with an issue and reference it in the PR.
- Keep pull requests scoped to one logical change.
- Include a clear description of what changed, why it changed, and how it was verified.
- Call out any follow-up work, assumptions, or known limitations directly in the PR description.

Before opening a PR, make sure:

- The branch is rebased or merged cleanly with current `main`
- Relevant tests pass locally
- Ruff and Black checks pass locally
- The PR checklist is completed

## Commit Conventions

Use short, imperative commit messages that match the repository's existing style:

- `feat: ...` for user-facing features
- `fix: ...` for bug fixes
- `docs: ...` for documentation-only changes
- `test: ...` for test-only changes
- `chore: ...` for tooling, metadata, and maintenance work
- `refactor: ...` for internal restructuring without behavior changes

Examples:

- `feat: add source ingest pipeline`
- `fix: anchor legacy notes to explicit session overrides`
- `chore: polish package metadata for release`

## Review Expectations

- Expect review comments to focus on correctness, boundaries, test coverage, and maintainability.
- If feedback is unclear, ask for clarification rather than guessing.
- Update tests and documentation alongside code when behavior changes.
