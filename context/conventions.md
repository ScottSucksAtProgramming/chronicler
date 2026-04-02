---
title: "D&D Session Scribe Conventions"
summary: "Stack choices, code patterns, module boundaries, and testing conventions"
created: 2026-04-02
updated: 2026-04-02
---

# D&D Session Scribe Conventions

## What Belongs Here

- Python source code in `src/session_scribe/` — modular package with clean architecture
- Prompt templates in `src/session_scribe/prompts/` (organized by module)
- Tests in `tests/` — mirrors the src structure
- Design specs and implementation plans in `docs/superpowers/`
- Sample PLAUD files for golden fixture testing

## What Does NOT Belong Here

- The Obsidian campaign vault — that lives in Scott's Obsidian vault directory (configured via SCRIBE_VAULT_PATH)
- LM Studio model files — managed by LM Studio externally
- General EMS transcript processing — that's `../EMScribe/`
- API keys or secrets — use `.env` (gitignored), never commit credentials

## Code Conventions

- **All data structures are Pydantic models.** No raw dicts passed between modules.
- **Type hints on everything.** Use `str | None` syntax (Python 3.12+), not `Optional[str]` in new code.
- **No file over ~300 lines.** If it's growing, split by responsibility.
- **Modules communicate through their `__init__.py` exports.** Never import from internal files directly.
- **Dependencies point inward.** Domain models don't import infrastructure. Extraction doesn't know about Obsidian. Vault manager doesn't know about nano-gpt.com.

## Module Boundaries

| Module | Responsibility | Depends On |
|--------|---------------|-----------|
| `models/` | Pydantic data structures | Nothing (pure domain) |
| `config/` | Settings from env vars | Nothing |
| `gateway/` | LLM API communication | `config/`, `models/` (for types only) |
| `cli/` | User-facing commands | Everything (thin delegation layer) |
| `ingestion/` (M2) | Parse PLAUD files | `models/`, `gateway/` |
| `extraction/` (M2) | Extract entities from sessions | `models/`, `gateway/` |
| `vault/` (M3) | Read/write Obsidian vault | `models/`, `config/` |
| `retrieval/` (M5) | Vector search over vault | `models/`, `config/` |
| `chat/` (M5) | Interactive Q&A TUI | `retrieval/`, `gateway/` |
| `reviewer/` (M4) | Vault quality passes | `vault/`, `gateway/` |

## Testing Conventions

- **TDD:** Write the test first, verify it fails, implement, verify it passes.
- **Unit tests:** No external dependencies. Mock LLM calls and filesystem.
- **Integration tests:** Marked with `@pytest.mark.integration`. Hit real services.
- **Golden fixtures:** Hand-labeled expected output from real sessions. Stored in `tests/fixtures/`.
- **User-style testing:** Manual QA after every milestone. Stories defined in the milestone plan.
- **Shared fixtures** live in `tests/conftest.py` (settings, tmp_vault).

## LLM Gateway Conventions

- All LLM calls go through `LLMGateway` — never call APIs directly.
- Prompts are versioned templates, not inline strings.
- Every LLM response is validated against a Pydantic schema.
- Structured output uses `complete_structured()` which handles JSON parsing and corrective retries.

## Git Conventions

- Feature commits: `feat: description`
- Bug fixes: `fix: description`
- Tests: `test: description`
- Scaffolding: `chore: description`
- All commits include `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>`
