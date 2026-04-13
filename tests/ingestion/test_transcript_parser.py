"""Tests for raw transcript parser."""

from chronicler.ingestion.transcript_parser import (
    parse_transcript,
)

SAMPLE_TRANSCRIPT = """00:00:00
Captain, and then you haven't gone back to see her because it is yeah.
00:00:56
I'm missing. Are there any trulies left in there?
00:01:27
Does anybody want the beer? Trevor. No, I'll FedEx it to you overnight.
"""


class TestParseTranscript:
    def test_parses_timestamped_segments(self):
        segments = parse_transcript(SAMPLE_TRANSCRIPT)
        assert len(segments) == 3
        assert segments[0].timestamp == "00:00:00"
        assert "Captain" in segments[0].text
        assert segments[1].timestamp == "00:00:56"
        assert segments[2].timestamp == "00:01:27"

    def test_segments_have_text(self):
        segments = parse_transcript(SAMPLE_TRANSCRIPT)
        for seg in segments:
            assert len(seg.text) > 0
            assert seg.text.strip() == seg.text

    def test_empty_input(self):
        segments = parse_transcript("")
        assert segments == []

    def test_no_timestamps(self):
        segments = parse_transcript("Just some text with no timestamps at all.")
        assert len(segments) == 1
        assert segments[0].timestamp == "00:00:00"

    def test_no_timestamps_splits_on_blank_lines_into_multiple_segments(self):
        text = (
            "The party boards the ship.\n"
            "The crew casts off.\n\n"
            "Later that night they argue about the chest.\n"
            "Seven keeps watch.\n\n"
            "At dawn they spot the shoreline."
        )
        segments = parse_transcript(text)

        assert len(segments) == 3
        assert segments[0].timestamp == "00:00:00"
        assert "boards the ship" in segments[0].text
        assert "argue about the chest" in segments[1].text
        assert "spot the shoreline" in segments[2].text

    def test_parses_real_session_022(self, session_022_dir):
        transcript_path = session_022_dir / "transcript.txt"
        text = transcript_path.read_text()
        segments = parse_transcript(text)

        assert len(segments) > 50
        assert segments[0].timestamp == "00:00:00"

        all_text = " ".join(s.text for s in segments)
        assert "Mayweather" in all_text

    def test_segments_are_in_order(self):
        segments = parse_transcript(SAMPLE_TRANSCRIPT)
        for i in range(len(segments) - 1):
            assert segments[i].timestamp <= segments[i + 1].timestamp
