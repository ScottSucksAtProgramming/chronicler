# Command Reference

Full reference for every `chronicler` command. Run `chronicler --help` or
`chronicler <command> --help` at any time for a quick reminder.

---

## `chronicler init`

Seeds the Obsidian vault with the folder structure and starter files Chronicler
expects. Safe to run on an existing vault — it only creates missing items.

```bash
chronicler init
```

---

## `chronicler party`

Manage the player character roster. PCs are tracked separately so the agent
never confuses them with NPCs during extraction.

### `chronicler party list`

Display all configured player characters.

```bash
chronicler party list
```

### `chronicler party add`

Create or update a player character note in the `Party/` folder.

```
Options:
  --player TEXT     Player name  [required]
  --character TEXT  Character name  [required]
  --class TEXT      Character class
```

```bash
chronicler party add --player "Alice" --character "Nyra" --class "Wizard"
```

### `chronicler party remove`

Delete a player character note from the `Party/` folder.

```
Options:
  --character TEXT  Character name  [required]
```

```bash
chronicler party remove --character "Nyra"
```

---

## `chronicler ingest`

Pass session recordings and source material to the agent for extraction and
vault population. The agent classifies each file automatically — session
exports, transcripts, lore documents, and general notes are all handled.

```
Arguments:
  FILES...  One or more files to ingest  [required]

Options:
  -s, --session INTEGER  Session number. Auto-detected from filename if omitted.
```

Accepted formats: `.pdf`, `.txt`, `.md`

```bash
# Ingest a session with an explicit number
chronicler ingest --session 12 /path/to/session-12.pdf

# Ingest a transcript alongside the PDF
chronicler ingest --session 12 /path/to/session-12.pdf /path/to/session-12.txt

# Ingest a lore document or campaign handout
chronicler ingest /path/to/world-primer.md
```

---

## `chronicler review`

Run a quality pass over the entire vault. Checks for broken wiki links,
missing required fields, duplicate entries, orphaned notes, and timeline gaps.
Findings are printed to the terminal and appended to `_Agent/Review-Log.md`.

```bash
chronicler review
```

---

## `chronicler improve`

Run deterministic vault maintenance. Backfills high-confidence relationships,
normalizes note formatting, and queues questions for ambiguous entities into
`_Agent/Questions/`. Safe to run at any time — it does not rewrite curated
prose.

```bash
chronicler improve
```

---

## `chronicler ask`

Display pending agent questions from `_Agent/Questions/`. In an interactive
terminal, you can answer each question inline and the response is appended to
the corresponding question file.

```bash
chronicler ask
```

---

## `chronicler reindex`

Rebuild the local embedding index from current vault contents. Requires LM
Studio to be running with an embedding model loaded. Index data is stored
under `.chronicler/` inside your vault directory.

```bash
chronicler reindex
```

---

## `chronicler chat`

Open the interactive campaign Q&A chat. The agent answers questions by
combining semantic retrieval from the index with direct vault reads. Requires
a completed `reindex` run.

```bash
chronicler chat
```

**In-chat commands:**

| Command | Action |
|---|---|
| `/help` | Show available chat commands |
| `/quit` | Exit the chat interface |

---

## `chronicler config`

Inspect and manage the persistent configuration file.

### `chronicler config show`

Print the active configuration and validate that the vault path exists.

```bash
chronicler config show
```

### `chronicler config init`

Run the interactive wizard to create or update `config.toml`. Pre-fills
existing values as defaults so you only need to change what has changed.

```bash
chronicler config init
```

---

## `chronicler stats`

Show extraction quality metrics accumulated across all ingested sessions,
including entity counts, confidence scores, and per-session breakdowns.

```bash
chronicler stats
```
