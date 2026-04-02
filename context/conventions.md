---
title: "D&D Session Scribe Conventions"
summary: "Stack choices, naming patterns, and integration boundaries for the Session Scribe agent"
created: 2026-04-02
updated: 2026-04-02
---

# D&D Session Scribe Conventions

## What Belongs Here

- Python service code for the extraction agent (FastAPI or async)
- Prompt templates for LM Studio/Qwen structured extraction
- Obsidian vault integration logic (REST API client)
- Configuration for whisper.cpp streaming parameters
- Optional live sidebar UI (Flask)

## What Does NOT Belong Here

- The Obsidian vault itself — that lives in Scott's Obsidian vault directory
- whisper.cpp source/binaries — those live in `../whisper.cpp/`
- LM Studio model files — managed by LM Studio externally
- General EMS transcript processing — that's `../EMScribe/`

## Stack Constraints

- **All inference is local.** LM Studio (Qwen) for extraction, whisper.cpp for transcription. No cloud API calls.
- **Obsidian integration** uses the Local REST API community plugin over HTTP. Requires the plugin enabled and an API key configured.
- **Audio capture** via PLAUD NotePin — the agent consumes whisper.cpp output, not raw audio.

## Build Phases

The PRD defines 5 phases. Work should proceed in order — each phase builds on the previous. See `prd.md` for details.
