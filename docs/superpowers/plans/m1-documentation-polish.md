# Plan: M1 — Documentation Polish

> Source PRD: [GitHub issue #1](https://github.com/ScottSucksAtProgramming/chronicler/issues/1)

## Editorial constraint

All changes to `README.md` must be **additive and targeted**. No existing prose is rewritten or restructured beyond the specific gap each phase addresses. Only `README.md` is modified across all three phases — no source code, tests, or CI configuration.

## Architectural decisions

This milestone has no technical architecture. The relevant editorial decisions are:

- **Platform notice placement**: two locations — a short blockquote/callout immediately after the intro paragraph (before Prerequisites), and an inline parenthetical on the Obsidian line inside Prerequisites.
- **`improve` placement**: a standalone note in Getting Started (not a numbered step), plus a Command Reference entry matching the existing heading-plus-one-sentence format used by every other command.
- **`ingest` framing**: session exports lead, general source material follows in a second sentence.
- **Clone URL**: replace the literal string `<your-remote-url>` with `https://github.com/ScottSucksAtProgramming/chronicler`.

---

## Phase 1: Safety & Setup Fixes

**User stories**: 1, 2, 3, 4

### What to build

Add a platform warning in two places so that a user on any platform knows macOS is required before they begin setup. Replace the placeholder clone URL with the real GitHub HTTPS URL so the copy-paste install command works.

The macOS warning appears as a short callout block (blockquote or bold line) placed after the project intro paragraph and before the Prerequisites heading. A second, inline note is added to the Obsidian desktop bullet inside Prerequisites.

The clone URL fix is a one-line replacement in the Installation section.

### Implementer notes

- The callout style (blockquote, `> [!WARNING]`, or bold line) should match whatever convention the README already uses — don't introduce a new pattern.
- Verify the clone URL fix in raw markdown source, not just the rendered preview. The angle brackets in `<your-remote-url>` may be consumed silently by some markdown renderers.

### Acceptance criteria

- [x] A macOS-only callout is visible between the intro paragraph and the Prerequisites heading when the README is rendered.
- [x] The Obsidian desktop bullet inside Prerequisites includes an inline macOS-only note (e.g. "macOS only").
- [x] The `git clone` command in the Installation section contains the literal URL `https://github.com/ScottSucksAtProgramming/chronicler` with no placeholder text.
- [x] No other prose in the README is changed.

---

## Phase 2: `improve` Command Discovery

**User stories**: 5, 6, 9

### What to build

Make `chronicler improve` discoverable from the README without prescribing it as a required first-run step.

Add a Command Reference entry for `improve` in the same format as every other command in that section: a bold or heading-level name followed by a one-sentence description of what it does.

Add a short note somewhere in the Getting Started section — after the numbered steps, not as a numbered step itself — indicating that `improve` can be run at any point for periodic vault maintenance.

After this phase, a user can learn about `improve` from either the command reference or the getting-started prose without having to run `chronicler --help`.

### Acceptance criteria

- [x] A `chronicler improve` entry appears in the Command Reference section in the same format as surrounding commands.
- [x] A note about `improve` appears in the Getting Started section and is clearly framed as optional/periodic (not a required numbered step).
- [x] Running `chronicler --help` confirms `improve` now appears in the README Command Reference (other command gaps, if any, are out of scope for this phase).
- [x] No other prose in the README is changed.

---

## Phase 3: `ingest` Description Update

**User stories**: 7, 8

### What to build

Update the `chronicler ingest` description in the README so users who want to import lore documents, world-building notes, or other non-session source material know that `ingest` accepts those files.

The update leads with session exports and PLAUD files (the primary use case) and adds a second sentence listing the additional accepted formats: markdown, plain text, and PDF.

This change applies to the Command Reference entry for `ingest`. Search the full README for every occurrence of the narrow "PLAUD session files" framing before assuming it only appears in the Command Reference — the Getting Started walkthrough is another likely location.

### Acceptance criteria

- [x] The `chronicler ingest` entry in Command Reference leads with session/PLAUD file framing.
- [x] A second sentence in that entry lists accepted general source formats (markdown, plain text, PDF).
- [x] Any other occurrence of the narrow "PLAUD session files only" framing in README is updated to match.
- [x] No other prose in the README is changed.
