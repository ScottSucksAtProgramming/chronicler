"""Extraction orchestrator — coordinates 3 sequential LLM calls to extract session data."""

import json
import logging
from typing import Any

from pydantic import BaseModel

from chronicler.extraction.prompts import (
    build_extraction_prompt,
    build_recap_prompt,
    build_quality_judge_prompt,
)
from chronicler.gateway.llm_gateway import LLMGateway
from chronicler.gateway.types import LLMRequest
from chronicler.models.context import ContextBundle
from chronicler.models.entities import NPC, Location, Faction, LootItem, PlotThread
from chronicler.models.extraction import AgentQuestion, ExtractionResult, QualityScore
from chronicler.models.session import NormalizedSession, SessionRecap, KeyEvent

logger = logging.getLogger(__name__)


class _RawEntities(BaseModel):
    """Typed intermediate container for raw entity extraction output."""

    npcs: list[NPC] = []
    locations: list[Location] = []
    factions: list[Faction] = []
    loot: list[LootItem] = []
    plot_threads: list[PlotThread] = []
    questions: list[AgentQuestion] = []


def _build_transcript_text(session: NormalizedSession) -> str | None:
    """Join in-game transcript segments into a single string."""
    in_game = [seg.text for seg in session.transcript_segments if seg.is_in_game]
    if not in_game:
        return None
    return "\n".join(in_game)


async def _extract_entities(
    summary: str | None,
    transcript: str | None,
    context: ContextBundle,
    gateway: Any,
    model: str,
) -> _RawEntities:
    """Call the LLM to extract entities and return a typed _RawEntities."""
    prompt = build_extraction_prompt(summary, transcript, context)
    request = LLMRequest(
        messages=[{"role": "user", "content": prompt}],
        model=model,
    )
    response = await gateway.complete(request)
    cleaned = LLMGateway._strip_code_fences(response.content)
    data = json.loads(cleaned)
    return _RawEntities.model_validate(data)


async def _generate_recap(
    summary: str,
    session_number: int,
    gateway: Any,
    model: str,
) -> SessionRecap:
    """Call the LLM to generate a session recap."""
    prompt = build_recap_prompt(summary, session_number)
    request = LLMRequest(
        messages=[{"role": "user", "content": prompt}],
        model=model,
    )
    response = await gateway.complete(request)
    cleaned = LLMGateway._strip_code_fences(response.content)
    data = json.loads(cleaned)

    key_events = [
        KeyEvent(description=e["description"], timestamp=e.get("timestamp"))
        for e in data.get("key_events", [])
    ]
    return SessionRecap(
        session_number=session_number,
        title=data["title"],
        summary=data["summary"],
        key_events=key_events,
    )


async def _evaluate_quality(
    source: str,
    entities: _RawEntities,
    recap: SessionRecap,
    gateway: Any,
    model: str,
) -> QualityScore | None:
    """Call the LLM to evaluate extraction quality. Returns None on any failure."""
    try:
        extraction_json = json.dumps(
            {
                "npcs": [n.model_dump() for n in entities.npcs],
                "locations": [location.model_dump() for location in entities.locations],
                "factions": [f.model_dump() for f in entities.factions],
                "loot": [li.model_dump() for li in entities.loot],
                "plot_threads": [pt.model_dump() for pt in entities.plot_threads],
                "recap": recap.model_dump(),
            },
            default=str,
        )

        prompt = build_quality_judge_prompt(source, extraction_json)
        request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        response = await gateway.complete(request)
        cleaned = LLMGateway._strip_code_fences(response.content)
        data = json.loads(cleaned)
        return QualityScore.model_validate(data)
    except Exception as exc:
        logger.warning("Quality evaluation failed: %s", exc)
        return None


async def extract_session(
    session: NormalizedSession,
    context: ContextBundle,
    gateway: Any,
    model: str,
) -> ExtractionResult:
    """Orchestrate 3 sequential LLM calls to extract a full ExtractionResult from a session.

    1. Entity extraction (NPCs, locations, factions, loot, plot threads, questions)
    2. Session recap generation
    3. Quality evaluation (LLM-as-judge)
    """
    summary = session.summary_text
    transcript = _build_transcript_text(session)

    # Step 1: Extract entities
    entities = await _extract_entities(summary, transcript, context, gateway, model)

    # Step 2: Generate recap
    source_text = summary or transcript or ""
    recap = await _generate_recap(source_text, session.session_number, gateway, model)

    # Step 3: Evaluate quality
    quality_score = await _evaluate_quality(
        source_text, entities, recap, gateway, model
    )

    return ExtractionResult(
        session_number=session.session_number,
        npcs=entities.npcs,
        locations=entities.locations,
        factions=entities.factions,
        loot=entities.loot,
        plot_threads=entities.plot_threads,
        recap=recap,
        questions=entities.questions,
        quality_score=quality_score,
    )
