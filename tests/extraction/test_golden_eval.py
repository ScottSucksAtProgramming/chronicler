"""Golden fixture evaluation tests for extraction quality.

These tests call the real LLM API and compare extraction results
against hand-labeled expected output. They are slow and costly,
so they're marked as integration tests.

Run with: pytest -m integration tests/extraction/test_golden_eval.py -v -s
"""

import asyncio
import pytest

from chronicler.ingestion import parse_plaud_pdf, parse_transcript
from chronicler.ingestion.normalizer import normalize_session
from chronicler.extraction import extract_session
from chronicler.models.context import ContextBundle
from chronicler.gateway.llm_gateway import LLMGateway
from chronicler.config.settings import Settings


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


async def _run_extraction(session_022_dir):
    """Run the full ingestion + extraction pipeline on Session 22."""
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
        return await extract_session(
            session=normalized,
            context=context,
            gateway=gateway,
            model=settings.nanogpt_model,
        )
    finally:
        await gateway.close()


# Module-level cache — extraction runs once, shared across all tests
_extraction_cache: dict[str, object] = {}


@pytest.mark.integration
class TestGoldenEval:
    """Evaluate extraction against the Session 22 golden fixture.

    The extraction pipeline runs ONCE via a module-level cache.
    All tests in this class share the same result.
    """

    def _get_result(self, session_022_dir):
        """Get or compute the extraction result (cached)."""
        if "result" not in _extraction_cache:
            _extraction_cache["result"] = asyncio.run(
                _run_extraction(session_022_dir)
            )
        return _extraction_cache["result"]

    def test_extraction_npc_recall(self, session_022_dir, session_022_golden):
        """Are we finding all the NPCs we should?"""
        result = self._get_result(session_022_dir)
        golden_npcs = {npc["name"] for npc in session_022_golden["npcs"]}
        extracted_npcs = {npc.name for npc in result.npcs}

        _, recall = _precision_recall(extracted_npcs, golden_npcs)
        print(f"\nNPC Recall: {recall:.1%}")
        print(f"  Extracted: {sorted(extracted_npcs)}")
        print(f"  Expected:  {sorted(golden_npcs)}")

        assert recall >= 0.5, f"NPC recall too low: {recall:.1%}"

    def test_extraction_location_recall(self, session_022_dir, session_022_golden):
        """Are we finding all the locations we should?"""
        result = self._get_result(session_022_dir)
        golden_locs = {loc["name"] for loc in session_022_golden["locations"]}
        extracted_locs = {loc.name for loc in result.locations}

        _, recall = _precision_recall(extracted_locs, golden_locs)
        print(f"\nLocation Recall: {recall:.1%}")

        assert recall >= 0.5, f"Location recall too low: {recall:.1%}"

    def test_extraction_has_recap(self, session_022_dir):
        """Does it produce a reasonable recap?"""
        result = self._get_result(session_022_dir)
        assert result.recap is not None
        assert len(result.recap.summary) > 100
        assert len(result.recap.key_events) >= 3

    def test_quality_score_above_threshold(self, session_022_dir):
        """Does the LLM-as-judge rate it acceptably?"""
        result = self._get_result(session_022_dir)
        if result.quality_score:
            print(f"\nQuality: {result.quality_score.model_dump()}")
            assert not result.quality_score.has_failures, (
                f"Quality failures: {result.quality_score.failed_dimensions}"
            )
