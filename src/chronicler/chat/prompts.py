# src/chronicler/chat/prompts.py
"""RAG chat prompt template for the D&D Chronicler assistant."""

from __future__ import annotations

from chronicler.chat.context_loader import DirectVaultNote
from chronicler.retrieval.retrieval import SearchResult


def build_chat_prompt(
    question: str,
    core_notes: list[DirectVaultNote],
    supporting_notes: list[DirectVaultNote],
    retrieval_results: list[SearchResult],
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
    lines.append(
        "You are a D&D campaign assistant with access to a vault of campaign notes."
    )
    lines.append(
        "Answer questions using ONLY the provided vault context below. "
        "When referencing a note, cite it using [[Note Name]] wikilinks. "
        "If the information is not in the provided context, "
        "say 'I don't have information about that in the vault.'"
    )
    lines.append(
        "Direct vault notes are authoritative. Retrieval hits are discovery aids and may be incomplete."
    )
    lines.append("Missing retrieval is not the same as missing vault data.")
    lines.append(
        "If direct notes and retrieval hits disagree, trust the direct vault notes and mention the conflict."
    )
    lines.append("do not present inferred relationships as confirmed facts.")
    lines.append(
        "When something is explicitly stated in a note, prefer phrasing like: 'The vault explicitly says ...'"
    )
    lines.append(
        "When you are connecting indirect evidence, prefer phrasing like: 'I infer ...'"
    )
    lines.append(
        "For definition questions such as 'What is X?', if no note directly defines X, say: 'I don't see a note that directly defines X.' Then give a clearly labeled inference only if the surrounding context supports one."
    )
    lines.append("")

    if core_notes:
        lines.append("## Core Vault Context")
        lines.append("")
        for note in core_notes:
            lines.append(f"From {note.path}:")
            lines.append(note.content)
            lines.append("")

    if supporting_notes:
        lines.append("## Directly Read Supporting Notes")
        lines.append("")
        for note in supporting_notes:
            lines.append(f"From {note.path}:")
            lines.append(note.content)
            lines.append("")

    # --- Retrieval context ---
    if retrieval_results:
        lines.append("## Retrieval Hits")
        lines.append("")
        for result in retrieval_results:
            source_label = f"From {result.path}"
            if result.heading:
                source_label += f" — {result.heading}:"
            lines.append(source_label)
            lines.append(result.content)
            lines.append("")
    else:
        lines.append("## Retrieval Hits")
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
