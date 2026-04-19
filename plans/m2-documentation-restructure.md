# Plan: M2 — Documentation Restructure

> Source PRD: [GitHub issue #2](https://github.com/ScottSucksAtProgramming/chronicler/issues/2)

## Editorial constraints

Durable decisions that apply across all phases:

- **Framing**: Chronicler is always described as an AI agent accessible through a CLI. Never "a CLI tool."
- **PLAUD**: The word "PLAUD" must not appear in any user-facing document after this milestone. Session files are "PDFs" or "transcripts." Internal source code identifiers (`parse_plaud_pdf`) are out of scope.
- **Platform**: macOS-only limitation is stated in README.md and docs/installation.md. No other doc needs to repeat it.
- **Install method**: pip install is the primary install method in all user-facing docs. The `uv sync` dev install is documented only in docs/development.md.
- **Ordering**: README is rewritten last (Phase 6) so every link it contains points to a file that already exists.
- **No code changes**: Only documentation files are created, moved, updated, or deleted. Source code and tests are untouched.
- **docs/ split**: `docs/installation.md`, `docs/quick-start.md`, `docs/commands.md`, `docs/configuration.md`, `docs/workflows.md`, `docs/troubleshooting.md` are user-facing. `docs/development.md` and `docs/ARCHITECTURE.md` are developer-facing.

---

## Phase 1: Cleanup & Housekeeping

**User stories**: 22, 23, 24, 25

### What to build

Get the repo into a clean, professional state before writing any new content. This phase has no new prose — it is entirely moves, deletions, a CHANGELOG fix, and one new short file (SECURITY.md).

Convert each item in `docs/future-improvements.md` to a standalone GitHub issue, then delete the file. Move all loose PRD and plan files from the repo root and `plans/` into the `docs/superpowers/` archive where historical artifacts live. Move `docs/interview-notes.md` into the same archive. Remove the single PLAUD mention from CHANGELOG.md. Create SECURITY.md at the repo root using GitHub's private vulnerability reporting as the contact method.

After this phase, the repo root contains no loose `.md` PRD or plan files, no user-facing document mentions PLAUD, and contributors have a clear security contact channel.

Note: `docs/article-brainstorm.md` is listed in `.gitignore` and is not tracked by git. It does not need to be archived — it is a private local file invisible to contributors.

### Acceptance criteria

- [ ] All 5 items from `docs/future-improvements.md` are filed as GitHub issues.
- [ ] `docs/future-improvements.md` is deleted.
- [ ] `prd.md` has been moved to `docs/superpowers/`.
- [ ] `prd-github-release.md` has been moved to `docs/superpowers/`.
- [ ] `prd-config-file-migration.md` has been moved to `docs/superpowers/`.
- [ ] `plans/github-public-release.md` has been moved to `docs/superpowers/plans/`.
- [ ] `plans/config-file-migration.md` has been moved to `docs/superpowers/plans/`.
- [ ] `plans/m1-documentation-polish.md` has been moved to `docs/superpowers/plans/`.
- [ ] `docs/interview-notes.md` has been moved to `docs/superpowers/`.
- [ ] `CHANGELOG.md` contains no occurrence of the word "PLAUD".
- [ ] `SECURITY.md` exists at the repo root and specifies GitHub private vulnerability reporting as the contact method.
- [ ] The repo root contains no loose `.md` PRD or plan files outside of `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `CLAUDE.md`, and `INDEX.md`.
- [ ] The `plans/` directory contains only `m2-documentation-restructure.md` (this plan file, to be archived in Phase 6 as the final act of the milestone).

---

## Phase 2: Installation & Quick Start

**User stories**: 3, 6, 7, 8, 9, 10

### What to build

Create the two documents that form the user onboarding path. A user who reads them in order should finish with a working vault and a successful first ingest.

`docs/installation.md` covers: the macOS-only platform requirement with a clear callout, the full prerequisites list (Python 3.12+, uv, Obsidian desktop, an LLM provider, and optionally LM Studio) with a one-line explanation of what each dependency does, pip install instructions, the global `uv tool install` as an alternative, the config wizard walkthrough with example prompts and values, and a verification step confirming the CLI is available.

`docs/quick-start.md` assumes installation is complete. It walks through the first-run sequence — `config init` → `init` → `party add` → `ingest` → `review` — with expected terminal output at each step so the user can confirm things are working. It closes with a pointer to `docs/workflows.md` for what to do next.

### Implementer notes

- `docs/installation.md` is the only user-facing doc besides the README that needs to state the macOS-only limitation. All other docs can assume the reader is on macOS.
- The config wizard walkthrough should show realistic example values (a made-up vault name, a placeholder API key format) rather than `<YOUR_VALUE_HERE>` placeholders.
- Do not mention PLAUD in either document.

### Acceptance criteria

- [ ] `docs/installation.md` exists and includes: macOS-only notice, prerequisites list with descriptions, pip install command, uv tool install alternative, config wizard walkthrough with example values, and a CLI verification step.
- [ ] `docs/quick-start.md` exists and covers the first-run sequence through a successful first ingest, with expected output at each step.
- [ ] `docs/quick-start.md` ends with a pointer to `docs/workflows.md` for ongoing use.
- [ ] Neither document contains the word "PLAUD".

---

## Phase 3: Reference Docs

**User stories**: 11, 12, 13

### What to build

Create the two lookup documents users return to repeatedly after first run.

`docs/commands.md` covers every command surfaced by `chronicler --help`. For each command: the full signature with all flags and options, a one-sentence description, and at least one usage example. Commands are ordered in the same logical sequence used in the README command listing (init, party, ingest, review, improve, ask, reindex, chat, config, stats).

`docs/configuration.md` documents every setting available in the config file and as an environment variable. For each setting: the config file key, the `CHRONICLER_`-prefixed environment variable name, whether it is required or optional, the default value if any, and a plain-language description. Settings are grouped by category: vault, LLM provider, embeddings/LM Studio, and logging. The doc includes an annotated example `config.toml` snippet and a note explaining that environment variables take precedence over the config file.

### Implementer notes

- Source flag names, types, and option sets for `docs/commands.md` from `chronicler --help` and `chronicler <command> --help`. Write original one-line descriptions — do not copy `--help` text verbatim, as it currently contains "PLAUD" in some places.
- Source settings for `docs/configuration.md` from `chronicler config show` against a working config AND cross-reference `src/chronicler/config/settings.py` directly to catch any settings that `config show` may not surface without a fully valid config.
- Do not mention PLAUD in either document.

### Acceptance criteria

- [ ] `docs/commands.md` exists with an entry for every command in `chronicler --help` output, including all flags and at least one example per command.
- [ ] Running `chronicler --help` and diffing against `docs/commands.md` reveals no undocumented commands or flags.
- [ ] `docs/configuration.md` exists with every setting documented: config key, env var name, required/optional, default, description.
- [ ] `docs/configuration.md` includes an annotated `config.toml` example and explains env var precedence.
- [ ] Neither document contains the word "PLAUD".

---

## Phase 4: Workflow & Troubleshooting Docs

**User stories**: 14, 15, 16, 17, 18

### What to build

Create the operational guides for users who are past first run.

`docs/workflows.md` contains three named, step-by-step workflows:
1. **Backlog Processing** — ingesting a queue of past sessions one at a time, covering the loop of ingest → review → improve → ask → next session.
2. **Active Campaign** — the after-session routine for ongoing play: ingest the newest session, review open threads, use chat before the next game.
3. **Knowledge Import** — ingesting non-session source material such as lore documents, setting guides, or handouts, and how it differs from session ingest.

`docs/troubleshooting.md` opens with a pre-flight checklist (verify Obsidian is running, vault name matches, LLM provider is configured, LM Studio is running if using embeddings). It then covers errors by category: Obsidian CLI errors, LLM provider errors, LM Studio/embeddings errors, config errors, and vault errors. Each error entry has: symptom, likely cause, and fix.

### Implementer notes

- The Knowledge Import workflow should note that general source files (markdown, plain text, PDF) are passed to `chronicler ingest` the same way session files are — the tool classifies them automatically.
- Do not mention PLAUD in either document.

### Acceptance criteria

- [ ] `docs/workflows.md` exists with all three named workflows: Backlog Processing, Active Campaign, and Knowledge Import.
- [ ] Each workflow in `docs/workflows.md` is step-by-step and references the correct commands.
- [ ] `docs/troubleshooting.md` exists with a pre-flight checklist section.
- [ ] `docs/troubleshooting.md` covers errors in at least four categories: Obsidian CLI, LLM provider, LM Studio/embeddings, and config errors.
- [ ] Neither document contains the word "PLAUD".

---

## Phase 5: Developer Doc

**User stories**: 19, 20

### What to build

Create `docs/development.md` so contributors can get a working dev environment without reading multiple files or guessing at conventions.

The document covers: cloning the repo and running `uv sync --dev` to create the dev environment, the commands for running unit tests and integration tests (and why integration tests require external services), the linting and formatting commands (`ruff check`, `black`), and a short note that CONTRIBUTING.md is the reference for branch conventions, PR process, and code style. It does not duplicate CONTRIBUTING.md — it complements it by covering the mechanics of the dev environment.

### Acceptance criteria

- [ ] `docs/development.md` exists and covers: dev environment setup, running unit tests, running integration tests, linting and formatting commands.
- [ ] The document directs readers to `CONTRIBUTING.md` for PR and code style conventions rather than duplicating that content.
- [ ] Following the document from scratch produces a working dev environment where `uv run pytest` passes.

---

## Phase 6: README Rewrite & Index Updates

**User stories**: 1, 2, 3, 4, 5, 24

### What to build

Rewrite `README.md` as a short, scannable landing page (~80 lines) that works on both PyPI and GitHub. Update `INDEX.md` and `CLAUDE.md` to reflect the final file structure.

The new README contains:
- An opening sentence describing Chronicler as an AI agent accessible via CLI (not "a CLI tool").
- The macOS-only platform callout.
- CI and PyPI badges.
- A pip install command as the primary installation method.
- A five-step quick-start summary (not a full walkthrough — just enough to show the shape of the workflow).
- A command listing with one-line descriptions and no deep examples.
- A Documentation section with links to all six docs files created in Phases 2–5.
- A Contributing section linking to `CONTRIBUTING.md` and `docs/development.md`.
- A License line.

`INDEX.md` is updated so its Active Documentation table includes all new docs files. `CLAUDE.md` tree is updated to reflect new files, moved files, and deleted files from all six phases.

### Implementer notes

- Every link in the new README (to docs files, to CONTRIBUTING.md, to ARCHITECTURE.md) must point to a file that already exists — all docs were created in Phases 1–5.
- The README should not reproduce content from any of the docs files. It links to them.
- Do not mention PLAUD anywhere in the README.
- The five-step quick-start summary in the README should differ from the full walkthrough in `docs/quick-start.md` — it is a taste, not a repeat.
- The last act of this phase is to move `plans/m2-documentation-restructure.md` to `docs/superpowers/plans/` and delete the now-empty `plans/` directory. Update CLAUDE.md accordingly.

### Acceptance criteria

- [ ] `README.md` is ~80 lines.
- [ ] The opening sentence describes Chronicler as an AI agent, not a CLI tool.
- [ ] A macOS-only callout is present.
- [ ] pip install is shown as the primary installation method.
- [ ] A five-step (or fewer) quick-start summary is present.
- [ ] A Documentation section links to all six new docs files and they all resolve.
- [ ] `README.md` contains no occurrence of the word "PLAUD".
- [ ] `INDEX.md` includes entries for all new docs files created in this milestone.
- [ ] `CLAUDE.md` tree accurately reflects the final repo structure including moved and deleted files.
- [ ] `plans/m2-documentation-restructure.md` has been moved to `docs/superpowers/plans/` and the `plans/` directory no longer exists.
