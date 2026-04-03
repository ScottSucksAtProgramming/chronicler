"""Tests for quality metrics tracking."""

import pytest

from session_scribe.vault.metrics import QualityMetrics, SessionMetric


class TestQualityMetrics:
    def test_add_metric(self, tmp_path) -> None:
        metrics = QualityMetrics(storage_path=tmp_path / "metrics.json")
        metrics.add(
            SessionMetric(
                session_number=22,
                npc_count=8,
                location_count=11,
                faction_count=2,
                thread_count=5,
                question_count=3,
                quality_score=4.2,
                reviewer_findings=14,
            )
        )

        assert len(metrics.all()) == 1
        assert metrics.all()[0].session_number == 22

    def test_metrics_persist(self, tmp_path) -> None:
        path = tmp_path / "metrics.json"

        metrics1 = QualityMetrics(storage_path=path)
        metrics1.add(
            SessionMetric(
                session_number=1,
                npc_count=3,
                location_count=2,
                faction_count=1,
                thread_count=2,
                question_count=0,
                quality_score=3.5,
                reviewer_findings=5,
            )
        )

        metrics2 = QualityMetrics(storage_path=path)
        assert len(metrics2.all()) == 1

    def test_metrics_summary(self, tmp_path) -> None:
        metrics = QualityMetrics(storage_path=tmp_path / "metrics.json")
        metrics.add(
            SessionMetric(
                session_number=1,
                npc_count=3,
                location_count=2,
                faction_count=1,
                thread_count=2,
                question_count=1,
                quality_score=3.5,
                reviewer_findings=10,
            )
        )
        metrics.add(
            SessionMetric(
                session_number=2,
                npc_count=5,
                location_count=4,
                faction_count=1,
                thread_count=3,
                question_count=0,
                quality_score=4.0,
                reviewer_findings=6,
            )
        )

        summary = metrics.summary()

        assert summary["sessions_processed"] == 2
        assert summary["avg_quality"] == pytest.approx(3.75)
        assert summary["findings_trend"] == "decreasing"
