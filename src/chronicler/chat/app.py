"""Textual TUI chat application for interactive campaign Q&A."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Input, Static

from chronicler.chat.context_loader import load_chat_context
from chronicler.chat.prompts import build_chat_prompt
from chronicler.gateway.llm_gateway import LLMGateway
from chronicler.gateway.types import LLMRequest
from chronicler.retrieval.retrieval import RetrievalLayer, SearchResult

if TYPE_CHECKING:
    from chronicler.vault.vault_manager import VaultManager


class ChatApp(App):
    """Textual chat app for querying D&D campaign notes via RAG."""

    TITLE = "Chronicler — Campaign Chat"

    CSS = """
    #messages {
        height: 1fr;
    }
    .user-msg {
        background: $primary-darken-2;
        margin: 1 2;
        padding: 1 2;
    }
    .assistant-msg {
        background: $surface;
        margin: 1 2;
        padding: 1 2;
    }
    .status-msg {
        color: $text-muted;
        margin: 0 4;
    }
    .error-msg {
        color: $error;
        margin: 1 2;
        padding: 1 2;
    }
    """

    def __init__(
        self,
        retrieval: RetrievalLayer,
        gateway: LLMGateway,
        model: str,
        vault_manager: "VaultManager | None" = None,
    ) -> None:
        super().__init__()
        self.retrieval = retrieval
        self.gateway = gateway
        self.model = model
        self.vault_manager = vault_manager
        self.conversation_history: list[dict[str, str]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Ask about your campaign...")

    def _scroll_down(self) -> None:
        self.query_one(VerticalScroll).scroll_end(animate=False)

    def _add_message(self, text: str, css_class: str) -> Static:
        messages = self.query_one("#messages", VerticalScroll)
        widget = Static(text, classes=css_class)
        messages.mount(widget)
        self._scroll_down()
        return widget

    @on(Input.Submitted)
    def handle_input(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return

        event.input.clear()

        if query.lower() == "/quit":
            self.exit()
            return

        if query.startswith("/"):
            self._handle_command(query)
            return

        self._add_message(f"You: {query}", "user-msg")
        self._run_query(query)

    def _handle_command(self, query: str) -> None:
        """Handle chat slash commands."""
        try:
            parts = shlex.split(query)
        except ValueError as exc:
            self._add_message(f"Error: {exc}", "error-msg")
            return

        command = parts[0].lower()

        if command == "/help":
            self._add_message(
                'Available commands: /help, /alias "alias" "entity", /quit',
                "assistant-msg",
            )
            return

        if command == "/alias":
            if self.vault_manager is None:
                self._add_message(
                    "Alias updates require a configured vault manager.",
                    "error-msg",
                )
                return
            if len(parts) != 3:
                self._add_message(
                    'Usage: /alias "alias" "entity"',
                    "error-msg",
                )
                return

            alias_term, entity_name = parts[1], parts[2]
            aliases = dict(self.vault_manager.read_agent_memory().entity_aliases)
            aliases[entity_name] = alias_term
            self.vault_manager.update_entity_aliases(aliases)
            self._add_message(
                f'Alias saved: "{alias_term}" -> "{entity_name}"',
                "assistant-msg",
            )
            return

        self._add_message(
            "Unknown command. Type /help for available commands.",
            "error-msg",
        )

    def _format_sources(self, context_bundle) -> str:
        """Format all note layers used to answer a query."""
        sources: set[str] = set()

        for note in context_bundle.core_notes:
            sources.add(note.path)

        for note in context_bundle.supporting_notes:
            sources.add(note.path)

        for result in context_bundle.retrieval_hits:
            label = result.path
            if result.heading:
                label += f" > {result.heading}"
            sources.add(label)

        return ", ".join(sorted(sources))

    @work(thread=True)
    def _run_query(self, query: str) -> None:
        """Run the RAG pipeline in a worker thread using sync methods.

        All calls are synchronous — no event loop needed in the thread.
        """
        status: Static | None = None

        try:
            # Search phase (sync)
            status = self.app.call_from_thread(
                self._add_message, "Searching vault...", "status-msg"
            )

            results: list[SearchResult] = self.retrieval.search_sync(query)
            context_bundle = (
                load_chat_context(
                    cli=(
                        self.vault_manager.cli
                        if self.vault_manager is not None
                        else None
                    ),
                    query=query,
                    retrieval_results=results,
                )
                if self.vault_manager is not None
                else None
            )

            # Update status
            self.app.call_from_thread(self._update_status, status, "Thinking...")

            # Build prompt
            prompt = build_chat_prompt(
                query,
                context_bundle.core_notes if context_bundle else [],
                context_bundle.supporting_notes if context_bundle else [],
                results,
                self.conversation_history,
            )
            request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )

            # Call LLM (sync)
            response = self.gateway.complete_sync(request)
            answer = response.content

            # Remove status widget
            self.app.call_from_thread(status.remove)

            # Build display text with sources
            display = f"Assistant: {answer}"
            if context_bundle is not None:
                sources = self._format_sources(context_bundle)
                if sources:
                    display += "\n\nSources: " + sources

            self.app.call_from_thread(self._add_message, display, "assistant-msg")

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": query})
            self.conversation_history.append({"role": "assistant", "content": answer})

        except Exception as exc:
            if status is not None:
                try:
                    self.app.call_from_thread(status.remove)
                except Exception:
                    pass
            self.app.call_from_thread(
                self._add_message,
                f"Error: {exc}",
                "error-msg",
            )

    def _update_status(self, widget: Static, text: str) -> None:
        widget.update(text)
