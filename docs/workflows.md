# Workflows

Three common patterns for using Chronicler. Each is a repeatable loop you can
run as often as you like.

---

## 1. Backlog Processing

Use this when catching up on past sessions. Work through them one at a time in
order so vault context builds correctly — each session's entities inform the
next.

### The loop (repeat for each session)

**1. Ingest the session**

```bash
chronicler ingest --session 3 /path/to/session-03.pdf
```

Always pass an explicit `--session` number when processing a backlog. The agent
uses it to anchor relationships and avoid mixing up sessions.

**2. Review the vault**

```bash
chronicler review
```

Scan the findings. New notes may have missing links, unresolved names, or
flagged duplicates. Review them in Obsidian before moving on.

**3. Run vault maintenance**

```bash
chronicler improve
```

Normalizes note structure and backfills high-confidence relationships discovered
across all sessions ingested so far. Safe to run after every session.

**4. Answer pending questions**

```bash
chronicler ask
```

The agent queues questions when it encounters ambiguity — an NPC with two
plausible factions, a location that might be the same as an existing one. Answer
them to keep the vault accurate.

**5. Move to the next session**

Repeat from step 1 with the next session number.

### Tips

- Ingest in chronological order. The vault context loaded at extraction time
  includes everything already written, so later sessions benefit from earlier
  ones being accurate.
- After every few sessions, open Obsidian and review the notes for anything the
  agent missed. Add corrections directly to the notes — the agent's managed
  sections won't overwrite your curated content.
- Run `chronicler stats` periodically to see extraction quality trends across
  sessions.

---

## 2. Active Campaign

Use this after each game session to keep the vault current.

### After-session routine

**1. Ingest the newest session**

```bash
chronicler ingest /path/to/latest-session.pdf
```

If your recorder exports a summary PDF and a transcript, pass both:

```bash
chronicler ingest /path/to/session.pdf /path/to/session.txt
```

**2. Review and triage**

```bash
chronicler review
chronicler ask
```

Address any questions or review findings while the session is fresh.

**3. Tidy the vault**

```bash
chronicler improve
```

**4. Rebuild the index**

```bash
chronicler reindex
```

Keeps the chat index current so `chronicler chat` has up-to-date context for
your next session.

### Before the next session

```bash
chronicler chat
```

Ask questions to refresh your memory: *"Who is Mira and why does the party
trust her?"* or *"What open plot threads involve the Merchant Guild?"*

---

## 3. Knowledge Import

Use this to get non-session material into your vault — published sourcebooks,
your own world-building notes, handouts, faction documents, or any campaign
reference you want the agent to know about.

### Importing source material

Pass files directly to `chronicler ingest`. The agent classifies each file
automatically — you don't need a separate command:

```bash
# Import a lore document
chronicler ingest /path/to/world-primer.md

# Import a PDF sourcebook excerpt
chronicler ingest /path/to/faction-guide.pdf

# Import multiple files at once
chronicler ingest /path/to/city-notes.md /path/to/timeline.txt
```

Accepted formats: `.pdf`, `.txt`, `.md`

### What gets written to the vault

Source material follows the same extraction path as session files. The agent
identifies entities (NPCs, locations, factions), writes or updates notes in
the appropriate vault folders, and archives the source file under
`_Agent/Sources/` for provenance.

Entities found in source material that already exist in the vault are enriched
— the agent adds a managed section with the new information rather than
overwriting your curated content.

### Tips

- Ingest source material before your backlog sessions so the context is
  available during extraction.
- If a document is strongly tied to a particular session (e.g. a handout given
  out during session 5), pass `--session 5` to anchor the import:

  ```bash
  chronicler ingest --session 5 /path/to/handout.pdf
  ```

- After importing, run `chronicler improve` to backfill any relationships the
  import surfaced.
