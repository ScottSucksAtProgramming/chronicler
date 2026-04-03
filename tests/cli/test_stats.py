"""Tests for stats and ingest-side metrics helpers."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from session_scribe.cli.main import app
from session_scribe.models.extraction import ExtractionResult, QualityScore
from session_scribe.models.session import SessionRecap

runner = CliRunner()


class TestStatsCommand:
    def test_stats_shows_no_metrics_message(self) -> None:
        mock_settings = MagicMock()
        mock_settings.vault_path = MagicMock()
        mock_settings.vault_name = "Test"

        with (
            patch("session_scribe.cli.main.Settings", return_value=mock_settings),
            patch("session_scribe.cli.main.QualityMetrics") as mock_metrics_cls,
        ):
            mock_metrics_cls.return_value.summary.return_value = {
                "sessions_processed": 0
            }

            result = runner.invoke(app, ["stats"])

        assert result.exit_code == 0
        assert "no quality metrics" in result.output.lower()

    def test_stats_shows_metrics_summary(self) -> None:
        mock_settings = MagicMock()
        mock_settings.vault_path = MagicMock()
        mock_settings.vault_name = "Test"

        with (
            patch("session_scribe.cli.main.Settings", return_value=mock_settings),
            patch("session_scribe.cli.main.QualityMetrics") as mock_metrics_cls,
        ):
            mock_metrics_cls.return_value.summary.return_value = {
                "sessions_processed": 2,
                "avg_quality": 3.75,
                "total_npcs": 8,
                "total_locations": 6,
                "findings_trend": "decreasing",
            }

            result = runner.invoke(app, ["stats"])

        assert result.exit_code == 0
        assert "2" in result.output
        assert "3.75" in result.output
        assert "decreasing" in result.output.lower()


class TestMetricLogging:
    def test_record_session_metric_uses_reviewer_findings(self, tmp_path) -> None:
        from session_scribe.cli.main import _record_session_metric

        settings = MagicMock()
        settings.vault_path = tmp_path

        result = ExtractionResult(
            session_number=7,
            npcs=[],
            locations=[],
            factions=[],
            loot=[],
            plot_threads=[],
            recap=SessionRecap(session_number=7, title="T", summary="S", key_events=[]),
            quality_score=QualityScore(
                completeness=4,
                accuracy=4,
                coherence=4,
                relevance=4,
                linking_quality=5,
            ),
        )

        report = MagicMock(total_findings=9)
        cli = MagicMock()

        with patch("session_scribe.cli.main.review_vault", return_value=report):
            _record_session_metric(settings, cli, result)

        from session_scribe.vault.metrics import QualityMetrics

        metrics = QualityMetrics(tmp_path / ".scribe" / "metrics.json")
        stored = metrics.all()
        assert len(stored) == 1
        assert stored[0].session_number == 7
        assert stored[0].reviewer_findings == 9
