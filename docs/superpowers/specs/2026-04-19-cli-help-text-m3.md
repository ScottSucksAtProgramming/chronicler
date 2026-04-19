# M3 — CLI Help Text

**Date:** 2026-04-19
**Status:** Draft

---

## Problem Statement

The `ingest` command's user-facing help text still describes the command as PLAUD-session-only,
even though the tool now accepts general campaign source material (markdown notes, plain-text
documents, and PDFs of any kind, in addition to PLAUD session exports). A user running
`chronicler --help` or `chronicler ingest --help` sees outdated framing that misrepresents the
command's actual capabilities and may cause them to miss the knowledge-import workflow entirely.

---

## Solution

Update the two user-facing strings in the `ingest` command so that the help output accurately
reflects its general-purpose ingest capability. No behaviour changes; no new flags; no new code
paths. This is a text-only milestone.

---

## User Stories

1. As a new user reading `chronicler --help`, I want the `ingest` summary line to mention both
   session recordings and source materials, so that I immediately understand the command handles
   more than just PLAUD exports.

2. As a user running `chronicler ingest --help`, I want the FILES argument description to name the
   accepted file extensions (.pdf, .txt, .md), so that I know which files I can pass without
   reading the documentation.

3. As a returning user who previously used `ingest` only for PLAUD PDFs, I want the updated help
   text to signal that markdown notes and plain-text sources are also accepted, so that I
   discover the knowledge-import workflow.

4. As a user who relies on `chronicler --help` as a quick reference, I want every user-facing
   string in the `ingest` command to be free of tool-specific jargon (PLAUD), so that the CLI
   feels like a general-purpose campaign tool rather than a PLAUD companion.

---

## Implementation Decisions

- **Only two user-facing strings change:**
  - The `ingest` command docstring (the one-liner shown in `chronicler --help`) changes to:
    `"Ingest session recordings and source materials into the campaign vault."`
  - The `FILES` positional argument `help=` string changes to:
    `"Source files to ingest. Accepts .pdf, .txt, and .md."`

- **Audit scope:** A full audit of user-facing strings in the `ingest` command confirms these are
  the only two strings containing PLAUD-specific references. Internal function names that
  reference PLAUD (e.g. `parse_plaud_pdf`) are implementation details and are out of scope.

- **No behaviour changes:** Routing logic, validation, file-type handling, and error messages are
  unchanged.

- **No new flags or options are added.**

---

## Testing Decisions

Good tests for this milestone verify observable CLI output, not implementation details.

- **What makes a good test:** Invoke the CLI via `typer.testing.CliRunner` and assert that the
  `--help` output contains (or does not contain) specific strings. Do not assert on internal
  function names or module structure.

- **Modules to test:**
  - `chronicler ingest --help` — assert the command docstring appears and contains no "PLAUD"
    references.
  - `chronicler ingest --help` — assert the FILES argument description appears and lists the
    three accepted extensions.
  - `chronicler --help` — assert the `ingest` one-liner appears and contains no "PLAUD"
    references.

- **Prior art:** `tests/cli/` contains existing CLI invocation tests using `CliRunner`. New tests
  follow the same pattern.

---

## Out of Scope

- Changing any routing logic, validation rules, or error messages.
- Updating internal function names (`parse_plaud_pdf`, etc.).
- Adding new file-type support.
- Updating any documentation files (covered by M2).
- Updating help text for any command other than `ingest`.

---

## Further Notes

This milestone is intentionally minimal. The two text changes unblock accurate public-facing
documentation and close the last visible PLAUD-only framing before the M4 release infrastructure
work begins.
