# Quick Start

This guide walks you through your first Chronicler session. It assumes
[installation and configuration](installation.md) are complete.

## Step 1 — Initialize the Vault

Create the folder structure Chronicler expects inside your Obsidian vault:

```bash
chronicler init
```

Expected output:

```
✓ Sessions/
✓ Party/
✓ NPCs/
✓ Locations/
✓ Factions/
✓ Loot/
✓ Plot-Threads/
✓ _Agent/
✓ _Dashboard.md
✓ Timeline.md
Vault initialized successfully.
```

Open Obsidian to confirm the folders appeared.

## Step 2 — Add Your Player Characters

Add each PC before ingesting sessions so the agent knows not to extract them
as NPCs:

```bash
chronicler party add --player "Alice" --character "Nyra" --class "Wizard"
chronicler party add --player "Ben" --character "Thorn" --class "Ranger"
```

Confirm the roster:

```bash
chronicler party list
```

Expected output:

```
Player Characters
─────────────────
Alice → Nyra (Wizard)
Ben   → Thorn (Ranger)
```

## Step 3 — Ingest a Session

Pass your session files to the agent. Provide a session number for best results:

```bash
chronicler ingest --session 1 /path/to/session-01-summary.pdf
```

Chronicler accepts PDFs, `.txt` transcripts, and `.md` notes — pass one or
more files together. The agent classifies each automatically.

Expected output:

```
Ingesting session 1...
  Parsing sources...
  Loading vault context...
  Extracting entities...
  Writing notes to vault...
    ✓ Sessions/Session-001.md
    ✓ NPCs/Mira-the-Innkeeper.md
    ✓ Locations/The-Rusty-Flagon.md
    ✓ Plot-Threads/The-Missing-Merchant.md
  Recording quality metrics...
Ingest complete. Quality score: 87/100
```

Open your vault in Obsidian to review the new notes.

## Step 4 — Review the Vault

Run a quality pass to surface missing links, orphaned notes, and open threads:

```bash
chronicler review
```

Expected output:

```
Vault Review
────────────
✓ No broken links
⚠ 2 NPCs missing faction tags
⚠ 1 open plot thread with no linked session
Findings appended to _Agent/Review-Log.md
```

Then check pending agent questions:

```bash
chronicler ask
```

Answer any questions inline to help the agent resolve ambiguities.

---

You now have a working vault with your first session ingested. Continue
with the [Workflows guide](workflows.md) to learn how to handle a session
backlog, set up the after-session routine, or import supplemental campaign
material.
