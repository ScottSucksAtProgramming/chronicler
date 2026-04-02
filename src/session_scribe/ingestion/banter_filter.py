"""LLM-assisted banter filter for classifying transcript segments."""

import json
import logging
from typing import Any

from session_scribe.gateway.llm_gateway import LLMGateway
from session_scribe.gateway.types import LLMRequest
from session_scribe.ingestion.transcript_parser import TimestampedSegment
from session_scribe.models.session import TranscriptSegment

logger = logging.getLogger(__name__)

BATCH_SIZE = 20

BANTER_FILTER_PROMPT = """\
You are an assistant helping to analyze transcripts from a tabletop RPG (D&D) session.

Your task is to classify each transcript segment as either in-game or out-of-game.

IN-GAME content includes:
- Characters speaking or acting within the fiction (dialogue, actions, descriptions)
- Game mechanics being discussed (rolls, abilities, rules clarifications during play)
- Dungeon Master narrating the world, NPCs, or scene descriptions
- Players describing what their characters do

OUT-OF-GAME content includes:
- Players chatting casually before or after the session
- Food, drinks, or snacks being discussed
- Real-world jokes, references, or unrelated conversations
- Technical issues (audio, video, connection problems)
- Scheduling or logistics discussions unrelated to the current game

You will be given a JSON array of segments, each with an "index" and "text" field.
Respond ONLY with a JSON object containing a "classifications" array.
Each classification must have "index" (matching the input) and "is_in_game" (boolean).

Example response:
{
  "classifications": [
    {"index": 0, "is_in_game": true},
    {"index": 1, "is_in_game": false}
  ]
}
"""


async def filter_banter(
    segments: list[TimestampedSegment],
    gateway: Any,
    model: str,
) -> list[TranscriptSegment]:
    """Classify transcript segments as in-game or out-of-game using an LLM.

    Processes segments in batches of BATCH_SIZE. On parse failure, defaults all
    segments in that batch to is_in_game=True (safe fallback — better to keep
    potential banter than lose game content).

    Args:
        segments: List of timestamped transcript segments to classify.
        gateway: LLMGateway instance to use for completions.
        model: Model identifier to use for the LLM call.

    Returns:
        List of TranscriptSegment Pydantic models with is_in_game set.
    """
    if not segments:
        return []

    results: list[TranscriptSegment] = []

    for batch_start in range(0, len(segments), BATCH_SIZE):
        batch = segments[batch_start : batch_start + BATCH_SIZE]
        batch_results = await _classify_batch(batch, gateway, model, batch_start)
        results.extend(batch_results)

    return results


async def _classify_batch(
    batch: list[TimestampedSegment],
    gateway: Any,
    model: str,
    index_offset: int,
) -> list[TranscriptSegment]:
    """Classify a single batch of segments via LLM.

    Returns TranscriptSegments with classifications applied. On any parse
    failure, all segments in the batch default to is_in_game=True.
    """
    segment_data = [
        {"index": i, "text": seg.text}
        for i, seg in enumerate(batch)
    ]

    prompt_content = (
        f"{BANTER_FILTER_PROMPT}\n\n"
        f"Segments to classify:\n{json.dumps(segment_data, indent=2)}"
    )

    request = LLMRequest(
        messages=[{"role": "user", "content": prompt_content}],
        model=model,
        temperature=0.0,
    )

    try:
        response = await gateway.complete(request)
        raw = LLMGateway._strip_code_fences(response.content)
        data = json.loads(raw)
        classifications = {
            item["index"]: item["is_in_game"]
            for item in data["classifications"]
        }
        logger.info(
            "Banter filter batch (offset=%d, size=%d): %d in-game, %d out-of-game — tokens=%d",
            index_offset,
            len(batch),
            sum(1 for v in classifications.values() if v),
            sum(1 for v in classifications.values() if not v),
            response.usage.total_tokens,
        )
    except Exception as exc:
        logger.warning(
            "Banter filter parse failure for batch at offset=%d: %s. Defaulting all to in_game=True.",
            index_offset,
            exc,
        )
        classifications = {i: True for i in range(len(batch))}

    return [
        TranscriptSegment(
            timestamp=seg.timestamp,
            text=seg.text,
            is_in_game=classifications.get(i, True),
        )
        for i, seg in enumerate(batch)
    ]
