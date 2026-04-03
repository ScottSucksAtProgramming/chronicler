# src/chronicler/retrieval/indexer.py
"""Vault indexer: chunks notes and stores embeddings in ChromaDB."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


@dataclass
class NoteChunk:
    """A single chunk of a vault note."""

    path: str
    heading: str
    content: str
    note_type: str = ""


def _extract_frontmatter_type(content: str) -> tuple[str, str]:
    """Return (note_type, content_without_frontmatter).

    Parses YAML frontmatter delimited by ``---`` and extracts the ``type``
    field if present.  Returns an empty string for the type when no
    frontmatter exists or the field is absent.
    """
    frontmatter_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = frontmatter_re.match(content)
    if not match:
        return "", content

    frontmatter_block = match.group(1)
    rest = content[match.end():]

    type_match = re.search(r"^type:\s*(.+)$", frontmatter_block, re.MULTILINE)
    note_type = type_match.group(1).strip() if type_match else ""
    return note_type, rest


class VaultIndexer:
    """Reads vault notes, chunks them, embeds, and upserts into ChromaDB."""

    def __init__(self, cli, embed_client, collection) -> None:
        self._cli = cli
        self._embed_client = embed_client
        self._collection = collection

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def chunk_note(path: str, content: str) -> list[NoteChunk]:
        """Split *content* into ``NoteChunk`` objects.

        Splitting is done on ``## `` headings.  Notes without any ``## ``
        heading are returned as a single chunk.  Empty sections are
        skipped.
        """
        note_type, body = _extract_frontmatter_type(content)

        # Split on level-2 headings
        parts = re.split(r"(?m)^## (.+)$", body)
        # parts layout: [preamble, heading1, section1, heading2, section2, ...]

        chunks: list[NoteChunk] = []

        if len(parts) == 1:
            # No ## headings — whole body is a single chunk
            text = parts[0].strip()
            if text:
                chunks.append(NoteChunk(path=path, heading="", content=text, note_type=note_type))
            else:
                # Completely empty note — still return one chunk so callers
                # don't have to handle zero-chunk notes for non-empty files.
                # (will be filtered later by index_vault)
                pass
            return chunks

        # preamble (text before first ## heading)
        preamble = parts[0].strip()
        if preamble:
            chunks.append(NoteChunk(path=path, heading="", content=preamble, note_type=note_type))

        # paired (heading, section) tuples
        for i in range(1, len(parts), 2):
            heading = parts[i].strip()
            section_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if section_text:
                chunks.append(
                    NoteChunk(
                        path=path,
                        heading=heading,
                        content=section_text,
                        note_type=note_type,
                    )
                )

        # If all sections were empty but preamble was also empty we still need
        # to return something sensible — return empty list and let caller decide.
        return chunks

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    @staticmethod
    def _read_vault_filesystem(vault_path: str) -> dict[str, str]:
        """Read all .md files from the vault filesystem directly (no CLI)."""
        result: dict[str, str] = {}
        vault = Path(vault_path)
        for md_file in vault.rglob("*.md"):
            rel_path = str(md_file.relative_to(vault))
            try:
                result[rel_path] = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
        return result

    async def index_vault(self, vault_path: str | None = None) -> int:
        """Index all vault notes into ChromaDB.

        Args:
            vault_path: Optional filesystem path to the vault. If provided,
                reads files directly (fast). Otherwise falls back to CLI.

        Returns the total number of chunks upserted.
        """
        if vault_path:
            notes = self._read_vault_filesystem(vault_path)
        else:
            notes = self._cli.read_all_notes()

        all_chunks: list[NoteChunk] = []
        for path, content in notes.items():
            if path.startswith("_Agent/Sources/"):
                logger.debug("Skipping archived source file: %s", path)
                continue
            if path.startswith("_Agent/"):
                logger.debug("Skipping agent file: %s", path)
                continue
            chunks = self.chunk_note(path, content)
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        total_upserted = 0
        for batch_start in range(0, len(all_chunks), BATCH_SIZE):
            batch = all_chunks[batch_start : batch_start + BATCH_SIZE]
            texts = [c.content for c in batch]

            embeddings: list[list[float]] = await self._embed_client.embed_batch(texts)

            ids = [f"{c.path}::{c.heading}" for c in batch]
            metadatas = [
                {"path": c.path, "heading": c.heading, "note_type": c.note_type}
                for c in batch
            ]

            self._collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            total_upserted += len(batch)
            logger.info(
                "Upserted batch of %d chunks (total so far: %d)",
                len(batch),
                total_upserted,
            )

        return total_upserted
