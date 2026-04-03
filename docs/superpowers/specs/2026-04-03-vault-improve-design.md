# Vault Improve Design

**Date:** 2026-04-03
**Status:** Approved for implementation

## Goal

Add a safe automatic maintenance pass that improves the vault over time without inventing facts or making ambiguous edits.

## Problem

Chronicler can now generate better new notes, but older notes remain inconsistent. Missing wikilinks, plain-string reference frontmatter, and stale formatting reduce graph quality and make the vault harder for both Obsidian and the agent to use well.

The existing `review` command can identify issues, but it does not apply safe fixes or route uncertain cases into a structured question flow.

## Approach

Introduce a new CLI command, `chronicler improve`, with a staged maintenance pipeline:

1. Scan supported notes across the vault
2. Apply deterministic, bounded fixes automatically
3. Generate question notes for ambiguous cases instead of guessing
4. Print a summary of changed files and created questions

This keeps the vault improving automatically while preserving safety.

## Supported Scope

### In Scope

- `Sessions/`
- `Party/`
- `NPCs/`
- `Locations/`
- `Factions/`
- `Loot/`

### Out Of Scope For V1

- rewriting summaries or lore prose
- inventing missing facts
- LLM-driven content enrichment
- broad cleanup of arbitrary markdown formatting
- deleting user-authored content

## Safe Auto-Fixes

The first version should only make deterministic changes:

- enrich missing body wikilinks for known entities
- normalize frontmatter reference fields to quoted wikilinks
- preserve existing user content outside the targeted rewrite areas
- skip files that cannot be parsed safely

The command should prefer no change over a risky change.

## Canonical Link Source

The maintenance pass should build a canonical link map from the existing vault:

- player characters from `Party/`
- NPCs from `NPCs/`
- locations from `Locations/`
- factions from `Factions/`
- loot from `Loot/`
- sessions from `Sessions/`

It may also incorporate aliases from `_Agent/Memory/entity-aliases.md` when they resolve unambiguously.

## Ambiguity Handling

When a fix is not deterministic, the command should not edit the note. Instead it should create a question in `_Agent/Questions/`.

Examples:

- one mention could map to multiple notes
- a likely entity mention has no clear canonical target
- a broken link has more than one plausible repair
- a note appears stale or sparse, but updating it would require interpretation

Each question should include:

- affected note path
- issue type
- short evidence snippet
- why the command did not auto-fix it
- the exact question for the user

## Command Behavior

`chronicler improve`

Default behavior:

- scan the supported folders
- apply deterministic maintenance fixes
- write ambiguity questions
- report counts for changed notes and created questions

The command should be safe to run repeatedly. A second run on an already-clean vault should be largely idempotent.

## Implementation Shape

Use a dedicated maintenance module rather than pushing this logic into the CLI or note renderer.

Suggested components:

- a vault scanner that builds canonical targets
- deterministic fixers for body links and frontmatter references
- a question writer for ambiguous findings
- a CLI entrypoint that orchestrates the pass and reports results

## Testing

- unit tests for canonical target discovery
- unit tests for deterministic note rewrites
- unit tests for ambiguity question generation
- CLI tests for summary output
- full test suite run after integration
