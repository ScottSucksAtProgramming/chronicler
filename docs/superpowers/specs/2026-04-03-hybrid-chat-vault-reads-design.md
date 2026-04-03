# Hybrid Chat Vault Reads Design

**Date:** 2026-04-03
**Status:** Approved for implementation

## Goal

Make `chronicler chat` use the vault as the real source of truth instead of treating the vector database as the whole knowledge boundary.

## Problem

The current chat flow only searches the Chroma index and sends the top retrieval chunks to the LLM. That creates two failure modes:

- the model acts as if missing retrieval results mean missing vault data
- core state such as `Party/` and `_Agent/Memory/` can be invisible unless those files happen to rank in the top search results

This contradicts the intended design that the vault, including the agent's memory notes, is authoritative.

## Approach

Adopt a hybrid chat pipeline:

1. Always read a fixed core set of vault files directly for every question
2. Use vector retrieval only for discovery of additional relevant notes
3. Directly read the files referenced by top retrieval results before prompting the LLM
4. Treat direct vault reads as more authoritative than raw retrieval chunks

## Core Direct-Read Context

For every chat turn, load these sources directly from the vault:

- `_Agent/Memory/vault-guide.md`
- all notes under `_Agent/Memory/`
- all notes under `Party/`
- `_Dashboard.md`
- `Timeline.md`
- `Plot-Threads/_Open-Threads.md`

This guarantees that party state, operational guidance, and persistent memory are visible on every turn.

## Vault Guide

Seed `_Agent/Memory/vault-guide.md` as an app-maintained but user-editable note.

The guide should document:

- which folders hold which information
- which notes are authoritative for party state, session history, threads, and agent memory
- that retrieval is discovery assistance, not authoritative truth
- that direct vault notes outrank retrieval chunks when they disagree

If the guide already exists, do not overwrite it during init.

## Retrieval Behavior

Keep semantic retrieval for discovery. After retrieval:

- collect the source file paths from the top results
- read the actual source notes from the vault
- include both the retrieved chunks and the full note reads in the final prompt

This allows retrieval to find relevant notes while letting the assistant verify answers against the real files.

## Prompt Structure

The chat prompt should distinguish between:

- core vault context
- directly read supporting notes
- retrieval hits
- conversation history
- current question

The prompt should instruct the model that:

- direct vault notes are authoritative
- retrieval hits are for discovery and may be incomplete
- missing retrieval is not the same as missing vault data
- conflicts between notes should be surfaced explicitly

## Correctness Rules

- Direct vault notes outrank retrieval chunks
- Retrieval chunks may support or narrow an answer but should not override a direct note
- If the vault contains conflicting information, the assistant should say so
- If a fact is absent from direct reads and retrieval, the assistant may say it is not available

## Scope

### In Scope

- hybrid chat context loader
- direct reading of core files and retrieval source notes
- seeding `vault-guide.md`
- prompt updates for context layering and authority rules
- tests covering the new chat context behavior

### Out Of Scope

- replacing Chroma retrieval entirely
- incremental reindexing improvements
- automatic memory writes from ordinary chat turns

## Verification

- add unit tests for the new context loader and prompt structure
- add/adjust chat tests so core context is always included
- run focused chat, vault, and CLI tests
- run the full test suite
