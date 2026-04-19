# Plan: M3 — CLI Help Text

> Source PRD: `docs/superpowers/specs/2026-04-19-cli-help-text-m3.md`

## Architectural decisions

- **Scope**: Text-only changes to the `ingest` command in the CLI entry point. No behaviour, routing, or logic changes.
- **Testing approach**: `typer.testing.CliRunner` invoked with `["ingest", "--help"]` and `["--help"]`; assert on stdout strings. No mocking of external services required.

---

## Phase 1: Update ingest help strings

**User stories**: 1, 2, 3, 4

### What to build

Replace the two PLAUD-specific user-facing strings in the `ingest` command:

- The command docstring (shown in `chronicler --help`) changes to:
  `"Ingest session recordings and source materials into the campaign vault."`
- The `FILES` positional argument `help=` string changes to:
  `"Source files to ingest. Accepts .pdf, .txt, and .md."`

No other strings, logic, or tests change in this phase.

### Acceptance criteria

- [ ] `chronicler --help` shows the updated `ingest` one-liner with no "PLAUD" references
- [ ] `chronicler ingest --help` shows the updated FILES description listing `.pdf`, `.txt`, and `.md`
- [ ] No other command output or behaviour is affected

---

## Phase 2: Add help-text regression tests

**User stories**: 1, 2, 4

### What to build

Add `CliRunner`-based tests in `tests/cli/` that lock in the correct help output and prevent silent regression. Follow the existing CLI test patterns in that directory.

Two test cases are needed:
1. Invoke `chronicler --help` and assert the `ingest` summary line contains "session recordings" and "source materials" and does not contain "PLAUD".
2. Invoke `chronicler ingest --help` and assert the FILES description contains `.pdf`, `.txt`, and `.md` and does not contain "PLAUD".

### Acceptance criteria

- [ ] Both tests pass with `uv run pytest tests/cli/`
- [ ] Neither test asserts on internal function names or implementation details — only on CLI stdout
- [ ] The test file follows the `CliRunner` pattern already established in `tests/cli/`
