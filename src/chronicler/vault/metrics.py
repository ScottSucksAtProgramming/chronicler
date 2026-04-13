"""Persistent quality metrics tracking for processed sessions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class SessionMetric:
    """Quality metrics recorded for a single processed session."""

    session_number: int
    npc_count: int
    location_count: int
    faction_count: int
    thread_count: int
    question_count: int
    quality_score: float
    reviewer_findings: int


class QualityMetrics:
    """JSON-backed store for session quality metrics."""

    def __init__(self, storage_path: Path) -> None:
        self._path = storage_path
        self._data = self._load()

    def _load(self) -> list[SessionMetric]:
        if not self._path.exists():
            return []

        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return [SessionMetric(**item) for item in raw]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([asdict(metric) for metric in self._data], indent=2),
            encoding="utf-8",
        )

    def add(self, metric: SessionMetric) -> None:
        """Append and persist a metric entry."""
        self._data.append(metric)
        self._save()

    def all(self) -> list[SessionMetric]:
        """Return all persisted metrics."""
        return list(self._data)

    def summary(self) -> dict[str, int | float | str]:
        """Return an aggregate view of tracked metrics."""
        if not self._data:
            return {"sessions_processed": 0}

        findings = [metric.reviewer_findings for metric in self._data]
        trend = "stable"
        if len(findings) >= 2:
            if findings[-1] < findings[0]:
                trend = "decreasing"
            elif findings[-1] > findings[0]:
                trend = "increasing"

        return {
            "sessions_processed": len(self._data),
            "avg_quality": sum(metric.quality_score for metric in self._data)
            / len(self._data),
            "total_npcs": sum(metric.npc_count for metric in self._data),
            "total_locations": sum(metric.location_count for metric in self._data),
            "findings_trend": trend,
        }
