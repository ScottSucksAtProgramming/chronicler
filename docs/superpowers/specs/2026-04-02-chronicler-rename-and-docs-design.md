# Chronicler Rename And Docs Design

**Date:** 2026-04-02
**Status:** Approved for implementation

## Goal

Prepare the project for publication and regular use by fully renaming it from Session Scribe to Chronicler, with `chronicler` as the canonical package and CLI name, and replace the placeholder documentation with a GitHub-ready README and onboarding guide.

## Scope

### In Scope

- Rename the Python package from `session_scribe` to `chronicler`
- Rename the CLI command from `scribe` to `chronicler`
- Rename configuration variables from `SCRIBE_*` to `CHRONICLER_*`
- Rename internal local app storage from `.scribe` to `.chronicler`
- Update user-facing strings, titles, and help text to use `Chronicler`
- Replace the empty `README.md` with complete setup and usage documentation
- Refresh `INDEX.md` so it reflects the current repository state

### Out Of Scope

- Rewriting historical milestone plan content for branding consistency
- Changing the underlying feature set or adding new product capabilities
- Preserving runtime compatibility aliases for old package names or old env vars

## Approach

Use a direct runtime rename rather than layering compatibility shims. This keeps the repo clean for remote publication and makes the code, install metadata, command surface, and docs align around one name.

Historical design and milestone artifacts remain in place as historical records. They may still reference the old name, but the active codebase and top-level docs will point readers to Chronicler as the supported interface.

## Runtime Changes

### Package And Imports

- Move `src/session_scribe/` to `src/chronicler/`
- Update imports across source and tests to the new package path
- Update package metadata in `pyproject.toml`

### CLI And Configuration

- Change the installed script to `chronicler`
- Update Typer app metadata, version output, help text, and command hints
- Rename `Settings` env prefix from `SCRIBE_` to `CHRONICLER_`
- Update error messages and `.env.example` accordingly

### Local Data

- Store app-managed artifacts under `.chronicler/` inside the configured vault
- Keep existing Chroma collection names unless the code requires a change

## Documentation Changes

### README

The new README should be the primary entry point for a generic GitHub reader and cover:

- What Chronicler does
- Current feature set
- Architecture at a high level
- Prerequisites
- Installation with `uv`
- Configuration using `.env`
- First-run workflow
- Command reference
- Typical operating workflow for session ingestion and chat
- Troubleshooting and known constraints

### INDEX

Refresh the index to point readers at:

- Core project docs
- The renamed package layout
- Current source modules
- Tests and fixtures
- Historical planning/spec materials as implementation background

## Testing And Verification

- Run focused tests that validate configuration loading, CLI wiring, and package imports after the rename
- Run the full test suite if feasible
- Run `uv run chronicler --help` and `uv run chronicler --version`
- Ensure README commands and env variable names match the implemented code

## Risks

- Package renames can miss import paths in tests or deferred imports
- CLI documentation can drift from actual command behavior if not verified directly
- Historical docs will still contain the old name, so active docs must clearly establish which surfaces are current
