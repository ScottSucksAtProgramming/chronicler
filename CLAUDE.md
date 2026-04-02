# D&D Live Session Scribe

## Purpose

Real-time AI agent that listens to a D&D session via PLAUD NotePin, transcribes it with whisper.cpp, extracts structured campaign data (NPCs, locations, plot hooks, loot) using a local LLM (LM Studio/Qwen), and auto-populates an Obsidian vault via the Local REST API plugin. Zero manual note-taking during or after play.

## Tree

```
dnd_notes_organizaer/
  CLAUDE.md
  INDEX.md
  prd.md
  docs/
    interview-notes.md
    superpowers/
      specs/
        2026-04-02-session-scribe-design.md
      plans/
        2026-04-02-milestone-1-foundation.md
  context/
    conventions.md
    lessons.md
```

## Rules

1. On session start within `dnd_notes_organizaer/`, read this file, then `INDEX.md`.
2. The PRD (`prd.md`) is the source of truth for project scope and phased build plan. Reference it before proposing new features or architecture changes.
3. This project reuses patterns from `../EMScribe/` (Python transcript processing) and `../whisper.cpp/` (ASR). Check those projects for reference implementations before building from scratch.
4. The target Obsidian vault structure is defined in the PRD. Do not deviate from it without discussing with Scott.
5. All LLM inference runs locally via LM Studio — no external API calls. Do not introduce cloud API dependencies.
6. When creating, renaming, or deleting files, update the Tree section above.
7. Follow the Note-Taking protocol below after completing tasks.

## Note-Taking

After completing any task — feature work, bug fix, discovery, or debugging session — append a dated one-liner to `context/lessons.md`.

**Format:**
```
- YYYY-MM-DD (scope): One-sentence lesson or discovery.
```

**When to write a lesson:**
- You learned something non-obvious about whisper.cpp streaming, LM Studio, or the Obsidian REST API.
- A timing assumption, chunk size, or deduplication approach surprised you.
- You made a mistake that future work should avoid.
- A design decision was validated or invalidated by testing.

Write lessons to either:
1. A context file in `context/` (if topic-specific)
2. `context/lessons.md` (if general)

If 3+ related lessons accumulate, extract into a dedicated context file and update the Tree.

## Lessons Learned

Running log lives in `context/lessons.md`. Read it at session start to catch non-obvious pitfalls before writing new code.

Escalated topic files (created when 3+ related lessons accumulate):
- *(none yet — add pointers here as topic files are created)*
