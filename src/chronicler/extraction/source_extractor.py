"""Extraction flow for non-transcript source documents."""

import json
import re

from chronicler.extraction.extractor import (
    _evaluate_quality,
    _generate_recap,
)
from chronicler.extraction.prompts import build_source_extraction_prompt
from chronicler.gateway.llm_gateway import LLMGateway
from chronicler.gateway.types import LLMRequest
from chronicler.models.context import ContextBundle
from chronicler.models.entities import Faction, Location, LootItem, NPC, PlotThread
from chronicler.models.extraction import AgentQuestion, KnowledgeIngestResult, QuestionPriority
from chronicler.models.source_document import SourceDocument
from chronicler.models.session import SessionRecap
from pydantic import BaseModel, Field


class _RawSourceEntities(BaseModel):
    npcs: list[NPC] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    factions: list[Faction] = Field(default_factory=list)
    loot: list[LootItem] = Field(default_factory=list)
    plot_threads: list[PlotThread] = Field(default_factory=list)
    questions: list[AgentQuestion] = Field(default_factory=list)


def _infer_source_attribution(document: SourceDocument) -> str | None:
    """Infer source attribution from document metadata or leading text."""
    if document.source_attribution:
        return document.source_attribution

    lines = [line.strip() for line in (document.extracted_text or "").splitlines()[:5] if line.strip()]
    for line in lines:
        lowered = line.lower()
        for prefix in ("source:", "author:", "from ", "by "):
            if not lowered.startswith(prefix):
                continue
            snippet = line[len(prefix):].strip(" .:-")
            if snippet:
                return snippet
    return None


def _fallback_source_attribution(document: SourceDocument) -> str:
    return f"Imported source: {document.original_filename}"


def _apply_source_provenance_defaults(
    data: dict,
    session_anchor: int | None,
    source_attribution: str | None,
    document: SourceDocument,
) -> dict:
    """Normalize raw extraction data before validating strict entity models."""
    if session_anchor is not None:
        return data

    fallback = source_attribution or _fallback_source_attribution(document)
    field_map = {
        "npcs": "first_appeared",
        "locations": "first_appeared",
        "factions": "first_appeared",
        "loot": "found_in",
        "plot_threads": "introduced_in",
    }
    for key, session_field in field_map.items():
        for item in data.get(key, []):
            if item.get(session_field) is None and not item.get("source_attribution"):
                item["source_attribution"] = fallback
    return data


def _infer_parent_location_from_description(location: dict) -> None:
    """Promote explicit containment phrases into ``parent_location`` when missing."""
    if location.get("parent_location"):
        return

    description = location.get("description") or ""
    match = re.search(
        r"\b(?:in|within)\s+([A-Z][A-Za-z' -]+?)(?:\s+(?:containing|contains|with|near)\b|[.,]|$)",
        description,
    )
    if not match:
        return

    candidate = match.group(1).strip()
    if candidate and candidate != location.get("name"):
        location["parent_location"] = candidate


def _normalize_location_relationships(data: dict) -> dict:
    """Fill in obvious explicit location hierarchy links that the model omitted."""
    for location in data.get("locations", []):
        _infer_parent_location_from_description(location)
    return data


async def extract_source_document(
    document: SourceDocument,
    context: ContextBundle,
    gateway,
    model: str,
) -> KnowledgeIngestResult:
    """Extract campaign knowledge from a general source document."""
    source_text = document.extracted_text or ""
    session_anchor = None
    if document.classification is not None:
        session_anchor = document.classification.session_anchor
    source_attribution = _infer_source_attribution(document)
    document.source_attribution = source_attribution

    prompt = build_source_extraction_prompt(
        source_text=source_text,
        context=context,
        source_label=document.original_filename,
        session_anchor=session_anchor,
        source_attribution=source_attribution,
    )
    request = LLMRequest(messages=[{"role": "user", "content": prompt}], model=model)
    response = await gateway.complete(request)
    cleaned = LLMGateway._strip_code_fences(response.content)
    data = json.loads(cleaned)
    data = _apply_source_provenance_defaults(
        data=data,
        session_anchor=session_anchor,
        source_attribution=source_attribution,
        document=document,
    )
    data = _normalize_location_relationships(data)
    entities = _RawSourceEntities.model_validate(data)

    recap = None
    if session_anchor is not None:
        recap = await _generate_recap(source_text, session_anchor, gateway, model)

    quality_recap = recap or SessionRecap(
        session_number=session_anchor or 0,
        title=document.original_filename,
        summary="Knowledge-first source ingest without session recap.",
        key_events=[],
    )
    quality_score = await _evaluate_quality(source_text, entities, quality_recap, gateway, model)

    questions = list(entities.questions)
    if session_anchor is None and source_attribution is None:
        questions.append(
            AgentQuestion(
                question="What source attribution should be recorded for this imported material?",
                context=f"Imported source '{document.original_filename}' did not clearly identify who authored or supplied it.",
                priority=QuestionPriority.MEDIUM,
            )
        )

    return KnowledgeIngestResult(
        session_number=session_anchor,
        npcs=entities.npcs,
        locations=entities.locations,
        factions=entities.factions,
        loot=entities.loot,
        plot_threads=entities.plot_threads,
        recap=recap,
        questions=questions,
        quality_score=quality_score,
    )
