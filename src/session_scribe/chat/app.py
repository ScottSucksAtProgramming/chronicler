"""Textual TUI chat application for interactive campaign Q&A."""

from __future__ import annotations

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Input, Static

from session_scribe.chat.prompts import build_chat_prompt
from session_scribe.gateway.llm_gateway import LLMGateway
from session_scribe.gateway.types import LLMRequest
from session_scribe.retrieval.retrieval import RetrievalLayer, SearchResult


class ChatApp(App):
    """Textual chat app for querying D&D campaign notes via RAG."""

    TITLE = "Session Scribe — Campaign Chat"

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
    ) -> None:
        super().__init__()
        self.retrieval = retrieval
        self.gateway = gateway
        self.model = model
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
    async def handle_input(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return

        event.input.clear()

        if query.lower() == "/quit":
            self.exit()
            return

        self._add_message(f"You: {query}", "user-msg")
        self._run_query(query)

    @work(thread=True)
    async def _run_query(self, query: str) -> None:
        """Run the RAG pipeline in a worker thread."""
        status: Static | None = None

        try:
            # Search phase
            status = self.app.call_from_thread(
                self._add_message, "Searching vault...", "status-msg"
            )

            results: list[SearchResult] = await self.retrieval.search(query)

            # Update status
            self.app.call_from_thread(self._update_status, status, "Thinking...")

            # Build prompt
            prompt = build_chat_prompt(query, results, self.conversation_history)
            request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )

            # Call LLM
            response = await self.gateway.complete(request)
            answer = response.content

            # Remove status widget
            self.app.call_from_thread(status.remove)

            # Build display text with sources
            display = f"Assistant: {answer}"
            if results:
                sources = set()
                for r in results:
                    label = r.path
                    if r.heading:
                        label += f" > {r.heading}"
                    sources.add(label)
                display += "\n\nSources: " + ", ".join(sorted(sources))

            self.app.call_from_thread(self._add_message, display, "assistant-msg")

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": query})
            self.conversation_history.append({"role": "assistant", "content": answer})

        except Exception as exc:
            if status is not None:
                self.app.call_from_thread(status.remove)
            self.app.call_from_thread(
                self._add_message,
                f"Error: {exc}",
                "error-msg",
            )

    def _update_status(self, widget: Static, text: str) -> None:
        widget.update(text)
