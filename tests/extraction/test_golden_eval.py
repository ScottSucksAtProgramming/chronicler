"""Golden fixture evaluation tests for extraction quality.

These tests call the real LLM API and compare extraction results
against hand-labeled expected output. They are slow and costly,
so they're marked as integration tests.

Run with: pytest -m integration tests/extraction/test_golden_eval.py -v -s
"""

import json
import pytest

from session_scribe.ingestion import parse_plaud_pdf, parse_transcript
from session_scribe.ingestion.normalizer import normalize_session
from session_scribe.extraction import extract_session
from session_scribe.models.context import ContextBundle
from session_scribe.gateway.llm_gateway import LLMGateway
from session_scribe.config.settings import Settings


def _precision_recall(extracted_names: set[str], expected_names: set[str]) -> tuple[float, float]:
    """Compute precision and recall between extracted and expected name sets.
    Uses lowercased comparison for fuzzy matching.
    """
    if not extracted_names and not expected_names:
        return 1.0, 1.0
    if not extracted_names:
        return 0.0, 0.0
    if not expected_names:
        return 0.0, 1.0

    extracted_lower = {n.lower() for n in extracted_names}
    expected_lower = {n.lower() for n in expected_names}

    true_positives = extracted_lower & expected_lower
    precision = len(true_positives) / len(extracted_lower) if extracted_lower else 0.0
    recall = len(true_positives) / len(expected_lower) if expected_lower else 0.0
    return precision, recall


# Module-level cache to avoid re-running the pipeline for each test
_extraction_cache: dict[str, object] = {}


@pytest.fixture
async def extraction_result(session_022_dir):
    """Run extraction once and cache the result across all tests."""
    if "result" not in _extraction_cache:
        settings = Settings()
        gateway = LLMGateway(settings)

        try:
            pdf = parse_plaud_pdf(session_022_dir / "summary.pdf")
            transcript_segs = parse_transcript(
                (session_022_dir / "transcript.txt").read_text()
            )

            normalized = await normalize_session(
                session_number=22,
                parsed_pdf=pdf,
                transcript_segments=transcript_segs,
                gateway=gateway,
                model=settings.nanogpt_model,
            )

            context = ContextBundle(session_number=22)
            _extraction_cache["result"] = await extract_session(
                session=normalized,
                context=context,
                gateway=gateway,
                model=settings.nanogpt_model,
            )
        finally:
            await gateway.close()

    return _extraction_cache["result"]


@pytest.mark.integration
class TestGoldenEval:
    """Evaluate extraction against the Session 22 golden fixture."""

    @pytest.mark.asyncio
    async def test_extraction_npc_recall(self, extraction_result, session_022_golden):
        golden_npcs = {npc["name"] for npc in session_022_golden["npcs"]}
        extracted_npcs = {npc.name for npc in extraction_result.npcs}

        _, recall = _precision_recall(extracted_npcs, golden_npcs)
        print(f"\nNPC Recall: {recall:.1%}")
        print(f"  Extracted: {sorted(extracted_npcs)}")
        print(f"  Expected:  {sorted(golden_npcs)}")
        print(f"  Missing:   {sorted(golden_npcs - {n.lower() for n in extracted_npcs})}")
        print(f"  Extra:     {sorted(extracted_npcs - {n.lower() for n in golden_npcs})}")

        assert recall >= 0.5, f"NPC recall too low: {recall:.1%}"

    @pytest.mark.asyncio
    async def test_extraction_location_recall(self, extraction_result, session_022_golden):
        golden_locs = {loc["name"] for loc in session_022_golden["locations"]}
        extracted_locs = {loc.name for loc in extraction_result.locations}

        _, recall = _precision_recall(extracted_locs, golden_locs)
        print(f"\nLocation Recall: {recall:.1%}")
        print(f"  Missing: {sorted(golden_locs - {n.lower() for n in extracted_locs})}")

        assert recall >= 0.5, f"Location recall too low: {recall:.1%}"

    @pytest.mark.asyncio
    async def test_extraction_has_recap(self, extraction_result):
        assert extraction_result.recap is not None
        assert len(extraction_result.recap.summary) > 100
        assert len(extraction_result.recap.key_events) >= 3

    @pytest.mark.asyncio
    async def test_quality_score_above_threshold(self, extraction_result):
        if extraction_result.quality_score:
            print(f"\nQuality: {extraction_result.quality_score.model_dump()}")
            assert not extraction_result.quality_score.has_failures, (
                f"Quality failures: {extraction_result.quality_score.failed_dimensions}"
            )
