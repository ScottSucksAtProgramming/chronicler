# Milestone 5: Retrieval + Chat — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a semantic search layer over the vault (ChromaDB + LM Studio embeddings) and an interactive Textual TUI chat where the user can ask natural language questions about their campaign, grounded in vault content.

**Architecture:** Two new modules: `retrieval/` manages ChromaDB vector store and LM Studio embeddings, `chat/` provides the Textual TUI. The retrieval layer indexes all vault notes as chunks, and semantic search finds relevant context for questions. The chat module sends the user's question + retrieved context to the LLM (via LLM Gateway) and displays the response with source citations. `scribe chat` launches the TUI, `scribe reindex` rebuilds the vector store.

**Tech Stack:** ChromaDB (vector store), LM Studio serving nomic-embed-text-v1.5 (embeddings via OpenAI-compatible API at localhost:1234), Textual (TUI framework), existing LLM Gateway (Kimi CLI)

**Spec:** `docs/superpowers/specs/2026-04-02-session-scribe-design.md` (Section 3 — Retrieval Layer, Chat Module; Section 7 — Milestone 5)

**Depends on:** Milestone 4 complete (vault with notes to search)

**Key integration points:**
- LM Studio embedding API: `POST http://localhost:1234/v1/embeddings` with model `text-embedding-nomic-embed-text-v1.5` — returns 768-dimensional vectors
- ChromaDB: local file-based persistent storage, no server needed
- Vault content: read via `ObsidianCLI.read_all_notes()` (filesystem bulk read, fast)
- LLM for answers: via existing `LLMGateway` (Kimi CLI or nano-gpt.com)

**IMPORTANT — Obsidian CLI zombie process lesson:** Minimize CLI subprocess calls. Use filesystem reads (`read_all_notes()`) for bulk operations. CLI only for search/backlinks when filesystem isn't sufficient.

---

## File Structure

```
src/session_scribe/
  retrieval/
    __init__.py          — exports: RetrievalLayer
    embeddings.py        — LM Studio embedding client
    indexer.py           — Index vault notes into ChromaDB
    retrieval.py         — Semantic search interface

  chat/
    __init__.py          — exports: launch_chat
    app.py               — Textual App class for the chat TUI
    prompts.py           — Prompt template for RAG (retrieval-augmented generation)

tests/
  retrieval/
    __init__.py
    test_embeddings.py
    test_indexer.py
    test_retrieval.py
  chat/
    __init__.py
    test_prompts.py
```

---

## Chunk 1: Embeddings + Indexer

### Task 1: Embedding Client

**Files:**
- Create: `src/session_scribe/retrieval/__init__.py`
- Create: `src/session_scribe/retrieval/embeddings.py`
- Create: `tests/retrieval/__init__.py`
- Create: `tests/retrieval/test_embeddings.py`

Thin wrapper around the LM Studio OpenAI-compatible embedding API.

- [ ] **Step 1: Create directories**

```bash
mkdir -p src/session_scribe/retrieval tests/retrieval
touch src/session_scribe/retrieval/__init__.py tests/retrieval/__init__.py
```

- [ ] **Step 2: Write failing tests**

```python
# tests/retrieval/test_embeddings.py
"""Tests for the LM Studio embedding client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from session_scribe.retrieval.embeddings import EmbeddingClient


@pytest.fixture
def client():
    return EmbeddingClient(
        base_url="http://localhost:1234/v1",
        model="text-embedding-nomic-embed-text-v1.5",
    )


class TestEmbeddingClient:
    @pytest.mark.asyncio
    async def test_embed_single_text(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3] * 256}],  # 768 dims
        }

        with patch.object(client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await client.embed("Test text")
            assert len(result) == 768

    @pytest.mark.asyncio
    async def test_embed_batch(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1] * 768},
                {"embedding": [0.2] * 768},
            ],
        }

        with patch.object(client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            results = await client.embed_batch(["Text 1", "Text 2"])
            assert len(results) == 2
            assert len(results[0]) == 768

    @pytest.mark.asyncio
    async def test_embed_empty_raises(self, client):
        with pytest.raises(ValueError):
            await client.embed("")

    def test_health_check(self, client):
        with patch("httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            assert client.health_check() is True

    def test_health_check_failure(self, client):
        with patch("httpx.get", side_effect=Exception("connection refused")):
            assert client.health_check() is False
```

- [ ] **Step 3: Run tests to verify they fail**

- [ ] **Step 4: Implement embedding client**

```python
# src/session_scribe/retrieval/embeddings.py
"""LM Studio embedding client using the OpenAI-compatible API."""

import logging
from typing import Sequence

import httpx

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


class EmbeddingClient:
    """Client for generating text embeddings via LM Studio.

    Uses the OpenAI-compatible POST /v1/embeddings endpoint.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url
        self.model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30)

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text string."""
        if not text.strip():
            raise ValueError("Cannot embed empty text")

        result = await self.embed_batch([text])
        return result[0]

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        response = await self._client.post(
            "/embeddings",
            json={"input": list(texts), "model": self.model},
        )
        response.raise_for_status()
        data = response.json()

        embeddings = [item["embedding"] for item in data["data"]]
        logger.info("Generated %d embeddings (model=%s)", len(embeddings), self.model)
        return embeddings

    def health_check(self) -> bool:
        """Check if the embedding API is reachable."""
        try:
            resp = httpx.get(f"{self.base_url}/models", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 5: Run tests:** `uv run pytest tests/retrieval/test_embeddings.py -v`
- [ ] **Step 6: Commit**

```bash
git add src/session_scribe/retrieval/ tests/retrieval/ pyproject.toml uv.lock
git commit -m "feat: add LM Studio embedding client for vector generation"
```

---

### Task 2: Vault Indexer (ChromaDB)

**Files:**
- Create: `src/session_scribe/retrieval/indexer.py`
- Create: `tests/retrieval/test_indexer.py`

Reads all vault notes, chunks them, generates embeddings, and stores in ChromaDB.

- [ ] **Step 1: Write failing tests**

```python
# tests/retrieval/test_indexer.py
"""Tests for vault indexer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from session_scribe.retrieval.indexer import VaultIndexer, NoteChunk


class TestNoteChunk:
    def test_chunk_creation(self):
        chunk = NoteChunk(
            path="NPCs/Theron.md",
            heading="Description",
            content="A ranger from the north.",
            note_type="npc",
        )
        assert chunk.path == "NPCs/Theron.md"
        assert chunk.note_type == "npc"


class TestVaultIndexer:
    def test_chunk_note_by_sections(self):
        content = (
            "---\ntype: npc\n---\n"
            "# Theron\n\n"
            "## Description\n\nA ranger from the north.\n\n"
            "## Key Interactions\n\n- Met the party in Session 1\n"
        )
        chunks = VaultIndexer.chunk_note("NPCs/Theron.md", content)

        assert len(chunks) >= 2
        assert any("ranger" in c.content for c in chunks)
        assert all(c.path == "NPCs/Theron.md" for c in chunks)

    def test_chunk_short_note_as_single_chunk(self):
        content = "# Short Note\n\nJust a brief note."
        chunks = VaultIndexer.chunk_note("Notes/short.md", content)

        assert len(chunks) == 1

    def test_chunk_skips_empty_sections(self):
        content = "# Title\n\n## Empty\n\n## Has Content\n\nSome text here."
        chunks = VaultIndexer.chunk_note("test.md", content)

        contents = [c.content for c in chunks]
        assert not any(c.strip() == "" for c in contents)

    @pytest.mark.asyncio
    async def test_index_vault(self):
        """Test that indexing reads notes and stores chunks."""
        mock_cli = MagicMock()
        mock_cli.read_all_notes.return_value = {
            "NPCs/Theron.md": "---\ntype: npc\n---\n# Theron\n\n## Description\n\nA ranger.",
            "Sessions/Session-001.md": "---\ntype: session\n---\n# Session 1\n\n## Summary\n\nThe party met.",
        }

        mock_embed_client = MagicMock()
        mock_embed_client.embed_batch = AsyncMock(return_value=[
            [0.1] * 768,
            [0.2] * 768,
        ])

        mock_collection = MagicMock()

        indexer = VaultIndexer(
            cli=mock_cli,
            embed_client=mock_embed_client,
            collection=mock_collection,
        )

        count = await indexer.index_vault()

        assert count >= 2
        mock_collection.upsert.assert_called()
        mock_embed_client.embed_batch.assert_called()

    @pytest.mark.asyncio
    async def test_index_skips_agent_files(self):
        """Agent internal files should not be indexed."""
        mock_cli = MagicMock()
        mock_cli.read_all_notes.return_value = {
            "_Agent/Memory/entity-aliases.md": "---\ntype: agent-memory\n---\n",
            "_Agent/Review-Log.md": "# Review Log\n",
            "NPCs/Theron.md": "# Theron\n\nA ranger.",
        }

        mock_embed_client = MagicMock()
        mock_embed_client.embed_batch = AsyncMock(return_value=[[0.1] * 768])

        mock_collection = MagicMock()

        indexer = VaultIndexer(
            cli=mock_cli,
            embed_client=mock_embed_client,
            collection=mock_collection,
        )

        count = await indexer.index_vault()

        # Should only index the NPC, not agent files
        assert count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement the indexer**

Key design:
- `NoteChunk` dataclass: path, heading, content, note_type
- `VaultIndexer.chunk_note(path, content)` — static method that splits a note by `## ` headings into chunks. Short notes become a single chunk. Skip empty sections. Extract `type` from frontmatter.
- `VaultIndexer.index_vault()` — reads all notes via `cli.read_all_notes()`, chunks them, embeds in batches, upserts into ChromaDB collection. Skips `_Agent/` files. Returns count of chunks indexed.
- ChromaDB IDs: `f"{path}::{heading}"` for uniqueness
- Batch embedding: process 50 chunks at a time to avoid overwhelming LM Studio

- [ ] **Step 4: Run tests:** `uv run pytest tests/retrieval/test_indexer.py -v`
- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/retrieval/indexer.py tests/retrieval/test_indexer.py
git commit -m "feat: add vault indexer — chunks notes and stores embeddings in ChromaDB"
```

---

### Task 3: Retrieval (Semantic Search)

**Files:**
- Create: `src/session_scribe/retrieval/retrieval.py`
- Create: `tests/retrieval/test_retrieval.py`
- Modify: `src/session_scribe/retrieval/__init__.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/retrieval/test_retrieval.py
"""Tests for semantic search retrieval."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from session_scribe.retrieval.retrieval import RetrievalLayer, SearchResult


class TestSearchResult:
    def test_creation(self):
        result = SearchResult(
            path="NPCs/Theron.md",
            heading="Description",
            content="A ranger from the north.",
            score=0.85,
        )
        assert result.score == 0.85
        assert result.path == "NPCs/Theron.md"


class TestRetrievalLayer:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["NPCs/Theron.md::Description"]],
            "documents": [["A ranger from the north."]],
            "metadatas": [[{"path": "NPCs/Theron.md", "heading": "Description"}]],
            "distances": [[0.15]],
        }

        mock_embed_client = MagicMock()
        mock_embed_client.embed = AsyncMock(return_value=[0.1] * 768)

        layer = RetrievalLayer(
            collection=mock_collection,
            embed_client=mock_embed_client,
        )

        results = await layer.search("Tell me about Theron", top_k=5)

        assert len(results) >= 1
        assert results[0].path == "NPCs/Theron.md"
        assert results[0].content == "A ranger from the north."

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        mock_collection = MagicMock()
        mock_embed_client = MagicMock()

        layer = RetrievalLayer(
            collection=mock_collection,
            embed_client=mock_embed_client,
        )

        results = await layer.search("", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        mock_embed_client = MagicMock()
        mock_embed_client.embed = AsyncMock(return_value=[0.1] * 768)

        layer = RetrievalLayer(
            collection=mock_collection,
            embed_client=mock_embed_client,
        )

        results = await layer.search("something obscure", top_k=5)
        assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement retrieval layer**

```python
# src/session_scribe/retrieval/retrieval.py
"""Semantic search over the vault using ChromaDB."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from session_scribe.retrieval.embeddings import EmbeddingClient

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result with source attribution."""

    path: str
    heading: str
    content: str
    score: float  # lower distance = more relevant


class RetrievalLayer:
    """Semantic search interface over the indexed vault."""

    def __init__(self, collection, embed_client: "EmbeddingClient") -> None:
        self.collection = collection
        self.embed_client = embed_client

    async def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search for vault content relevant to the query."""
        if not query.strip():
            return []

        query_embedding = await self.embed_client.embed(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                search_results.append(SearchResult(
                    path=results["metadatas"][0][i].get("path", ""),
                    heading=results["metadatas"][0][i].get("heading", ""),
                    content=results["documents"][0][i],
                    score=results["distances"][0][i],
                ))

        logger.info("Search '%s': %d results", query[:50], len(search_results))
        return search_results
```

- [ ] **Step 4: Update retrieval exports**

```python
# src/session_scribe/retrieval/__init__.py
"""Public API for the retrieval module."""
from session_scribe.retrieval.retrieval import RetrievalLayer, SearchResult
from session_scribe.retrieval.embeddings import EmbeddingClient, EmbeddingError
from session_scribe.retrieval.indexer import VaultIndexer, NoteChunk
__all__ = ["RetrievalLayer", "SearchResult", "EmbeddingClient", "EmbeddingError", "VaultIndexer", "NoteChunk"]
```

- [ ] **Step 5: Run tests:** `uv run pytest tests/retrieval/ -v`
- [ ] **Step 6: Commit**

```bash
git add src/session_scribe/retrieval/ tests/retrieval/
git commit -m "feat: add semantic search retrieval layer with ChromaDB"
```

---

## Chunk 2: Chat TUI + CLI Wiring

### Task 4: RAG Prompt Template

**Files:**
- Create: `src/session_scribe/chat/__init__.py`
- Create: `src/session_scribe/chat/prompts.py`
- Create: `tests/chat/__init__.py`
- Create: `tests/chat/test_prompts.py`

- [ ] **Step 1: Create directories**

```bash
mkdir -p src/session_scribe/chat tests/chat
touch src/session_scribe/chat/__init__.py tests/chat/__init__.py
```

- [ ] **Step 2: Write failing tests**

```python
# tests/chat/test_prompts.py
"""Tests for the RAG chat prompt template."""

from session_scribe.chat.prompts import build_chat_prompt
from session_scribe.retrieval.retrieval import SearchResult


class TestBuildChatPrompt:
    def test_includes_question(self):
        prompt = build_chat_prompt(
            question="What do we know about Sylvie?",
            context_results=[],
            conversation_history=[],
        )
        assert "Sylvie" in prompt

    def test_includes_context(self):
        results = [
            SearchResult(path="NPCs/Sylvie.md", heading="Description",
                        content="Leader of the cult's smuggling operation.", score=0.1),
        ]
        prompt = build_chat_prompt(
            question="Who is Sylvie?",
            context_results=results,
            conversation_history=[],
        )
        assert "smuggling" in prompt
        assert "NPCs/Sylvie.md" in prompt

    def test_includes_conversation_history(self):
        history = [
            {"role": "user", "content": "Tell me about the tunnels"},
            {"role": "assistant", "content": "There are six earthen tunnels..."},
        ]
        prompt = build_chat_prompt(
            question="How many were there?",
            context_results=[],
            conversation_history=history,
        )
        assert "tunnels" in prompt

    def test_instructs_source_citation(self):
        prompt = build_chat_prompt(
            question="test",
            context_results=[],
            conversation_history=[],
        )
        assert "source" in prompt.lower() or "cite" in prompt.lower()

    def test_instructs_no_hallucination(self):
        prompt = build_chat_prompt(
            question="test",
            context_results=[],
            conversation_history=[],
        )
        assert "don't know" in prompt.lower() or "not in" in prompt.lower()
```

- [ ] **Step 3: Implement prompt template**

The prompt should:
- Include the user's question
- Include retrieved vault context with source paths
- Include recent conversation history for multi-turn
- Instruct the LLM to cite sources (`[[Note Name]]`)
- Instruct the LLM to say "I don't have information about that" rather than hallucinating
- Be grounded in vault content only

- [ ] **Step 4: Run tests:** `uv run pytest tests/chat/ -v`
- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/chat/ tests/chat/
git commit -m "feat: add RAG chat prompt template with source citation instructions"
```

---

### Task 5: Textual Chat TUI

**Files:**
- Create: `src/session_scribe/chat/app.py`

This is the interactive chat application using Textual. It needs:
- A text input at the bottom for typing questions
- A scrolling message area showing the conversation
- User messages on one side, assistant responses on the other
- Source citations rendered as clickable-looking references
- Loading indicator while waiting for LLM response
- Ctrl+C or `/quit` to exit

**Implementation approach:**
- Textual `App` with a `VerticalScroll` for messages and an `Input` widget
- On submit: embed query → search ChromaDB → build RAG prompt → call LLM → display response
- Store conversation history in memory (not persisted)
- The app takes `RetrievalLayer` and `LLMGateway` as constructor args

- [ ] **Step 1: Implement the chat app**

The TUI should be a `textual.app.App` subclass called `ChatApp`. Key components:
- `Header` showing "Session Scribe — Campaign Chat"
- `VerticalScroll` container for message bubbles
- `Input` widget at bottom with placeholder "Ask about your campaign..."
- `Static` widgets for each message (user in one color, assistant in another)
- Status bar showing "Searching..." / "Thinking..." during processing

Since Textual apps are hard to unit test, focus on integration testing in the user-style testing phase. The prompt template (Task 4) handles the testable logic.

- [ ] **Step 2: Commit**

```bash
git add src/session_scribe/chat/app.py
git commit -m "feat: add Textual chat TUI for campaign Q&A"
```

---

### Task 6: Wire CLI Commands (chat + reindex)

**Files:**
- Modify: `src/session_scribe/cli/main.py` — replace `chat` and `reindex` stubs

- [ ] **Step 1: Wire `scribe reindex`**

Replace the stub with:
1. Load Settings
2. Create ObsidianCLI, EmbeddingClient
3. Create/get ChromaDB collection (persistent, stored alongside vault)
4. Create VaultIndexer
5. Call `indexer.index_vault()`
6. Print count of chunks indexed

ChromaDB storage path: `{vault_path}/.scribe/chromadb/` — a hidden directory inside the vault.

- [ ] **Step 2: Wire `scribe chat`**

Replace the stub with:
1. Load Settings
2. Check LM Studio health (embedding client)
3. Create/get ChromaDB collection
4. Create RetrievalLayer, LLMGateway
5. Launch `ChatApp` TUI
6. Handle errors gracefully (LM Studio not running, no index)

If ChromaDB collection is empty (no index), print a message suggesting `scribe reindex` first.

- [ ] **Step 3: Add `scribe chat` launch test**

```python
# tests/cli/test_chat_launch.py
"""Tests for the chat CLI command."""

from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from session_scribe.cli.main import app

runner = CliRunner()


class TestChatCommand:
    def test_chat_help(self):
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0

    def test_reindex_help(self):
        result = runner.invoke(app, ["reindex", "--help"])
        assert result.exit_code == 0
```

- [ ] **Step 4: Run ALL tests:** `uv run pytest -v`
- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/cli/ src/session_scribe/chat/ tests/cli/
git commit -m "feat: wire scribe chat and reindex commands to retrieval + TUI"
```

---

## Chunk 3: User-Style Testing

### Task 7: Full User-Style Testing

**ALL stories must pass. No skipping.**

- [ ] **Story 1:** "I run `scribe reindex` — does it index the vault?"

```bash
uv run scribe reindex
```

Verify: Shows count of chunks indexed. No errors. ChromaDB files created in vault.

- [ ] **Story 2:** "I run `scribe chat` — does the TUI launch cleanly?"

```bash
uv run scribe chat
```

Verify: TUI launches. Shows header. Input field at bottom. Can type.

- [ ] **Story 3:** "I ask 'What do we know about Sylvie?' — comprehensive answer with citations?"

Type the question in the chat TUI. Verify: Answer mentions cult leader, smuggling, The Black Spire. Cites `[[Sylvie]]` or `NPCs/Sylvie.md`.

- [ ] **Story 4:** "I ask 'What are our open plot threads?' — matches vault?"

Verify: Lists threads from _Open-Threads.md.

- [ ] **Story 5:** "I ask 'What happened with the boat?' — figures out Mayweather?"

Verify: Answer talks about the Mayweather and its chemicals/cult connection.

- [ ] **Story 6:** "I ask about something not in the vault — does it say it doesn't know?"

Ask about something completely unrelated (e.g., "What happened in Waterdeep?"). Verify: Says it doesn't have information about that.

- [ ] **Story 7:** "Multi-turn conversation — does it maintain context?"

Ask "Tell me about the tunnels." Then ask "How many were there?" Verify: Second answer knows you mean the tunnels.

- [ ] **Story 8:** "I ask 'When did we first encounter the cult?' — does it find the right session?"

Ask this temporal question. Verify: Answer references Session 22 or the correct session where the cult was first mentioned.

- [ ] **Story 9:** "Is the TUI responsive and pleasant?"

Verify: Messages render cleanly. No visual glitches. Scrolling works. Exit with Ctrl+C works.

- [ ] **Story 9:** "LM Studio not running — clear error?"

Stop LM Studio, then try `scribe chat`. Verify: Clear error message about LM Studio being unreachable.

- [ ] **Story 10:** "I run `scribe reindex` after manually editing notes — index updates?"

Edit a note in Obsidian, then run `scribe reindex`. Verify: New content is searchable.

- [ ] **Story 11:** "LLM provider (Kimi) is slow/down — does chat handle it gracefully?"

Kill the Kimi CLI or disconnect network. Ask a question in chat. Verify: Clear error message about the LLM being unavailable, not a crash or hang.

- [ ] **Story 12:** "Full test suite passes"

```bash
uv run pytest -v
```

Document all issues, fix them, re-test. Commit fixes.

---

## Summary

After completing all tasks, Milestone 5 adds:

- **Embedding client:** LM Studio integration for nomic-embed-text-v1.5 (768-dim vectors)
- **Vault indexer:** Chunks notes by section, generates embeddings, stores in ChromaDB
- **Retrieval layer:** Semantic search returning ranked results with source attribution
- **RAG chat prompt:** Grounded in vault content, instructs citation and no-hallucination
- **Textual chat TUI:** Interactive campaign Q&A with conversation history
- **`scribe reindex`:** Rebuilds vector store from current vault contents
- **`scribe chat`:** Launches the interactive TUI
- **12 user-style testing stories:** All must pass
