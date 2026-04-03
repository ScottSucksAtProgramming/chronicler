# src/session_scribe/chat/prompts.py
"""RAG chat prompt template for the D&D Session Scribe assistant."""

from __future__ import annotations

from session_scribe.retrieval.retrieval import SearchResult


def build_chat_prompt(
    question: str,
    context_results: list[SearchResult],
    conversation_history: list[dict[str, str]],
) -> str:
    """Build a retrieval-augmented generation prompt.

    Args:
        question: The user's current question.
        context_results: Relevant vault chunks retrieved via semantic search.
        conversation_history: Prior turns as ``[{"role": ..., "content": ...}]``.

    Returns:
        A fully-formed prompt string ready to send to the LLM.
    """
    lines: list[str] = []

    # --- System instructions ---
    lines.append("You are a D&D campaign assistant with access to a vault of campaign notes.")
    lines.append(
        "Answer questions using ONLY the provided vault context below. "
        "When referencing a note, cite it using [[Note Name]] wikilinks. "
        "If the information is not in the provided context, "
        "say 'I don't have information about that in the vault.'"
    )
    lines.append("")

    # --- Vault context ---
    if context_results:
        lines.append("## Vault Context")
        lines.append("")
        for result in context_results:
            source_label = f"From {result.path}"
            if result.heading:
                source_label += f" — {result.heading}:"
            lines.append(source_label)
            lines.append(result.content)
            lines.append("")
    else:
        lines.append("## Vault Context")
        lines.append("")
        lines.append("(No relevant vault notes found.)")
        lines.append("")

    # --- Conversation history ---
    if conversation_history:
        lines.append("## Conversation History")
        lines.append("")
        for turn in conversation_history:
            role = turn.get("role", "user").capitalize()
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")
        lines.append("")

    # --- Current question ---
    lines.append("## Question")
    lines.append("")
    lines.append(question)

    return "\n".join(lines)
