# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for model_triage_result (OMN-9322 sub-1)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from omnibase_core.models.triage import (
    EnumProbeStatus,
    EnumTriageBlastRadius,
    EnumTriageFreshness,
    EnumTriageSeverity,
    ModelTriageFinding,
    ModelTriageProbeResult,
    ModelTriageReport,
    rank_findings,
)


def _finding(
    severity: EnumTriageSeverity = EnumTriageSeverity.MEDIUM,
    freshness: EnumTriageFreshness = EnumTriageFreshness.LIVE,
    blast: EnumTriageBlastRadius = EnumTriageBlastRadius.REPO,
    probe: str = "test_probe",
    message: str = "test finding",
) -> ModelTriageFinding:
    return ModelTriageFinding(
        source_probe=probe,
        severity=severity,
        freshness=freshness,
        blast_radius=blast,
        message=message,
    )


class TestSeverityOrdering:
    def test_weights_are_monotonic_descending(self) -> None:
        """CRITICAL > HIGH > MEDIUM > LOW > INFO."""
        weights = [s.weight for s in EnumTriageSeverity]
        assert weights == sorted(weights, reverse=True)

    def test_freshness_weights_monotonic(self) -> None:
        assert EnumTriageFreshness.LIVE.weight > EnumTriageFreshness.RECENT.weight
        assert EnumTriageFreshness.RECENT.weight > EnumTriageFreshness.STALE.weight
        assert EnumTriageFreshness.STALE.weight > EnumTriageFreshness.MISSING.weight

    def test_blast_radius_weights_monotonic(self) -> None:
        assert EnumTriageBlastRadius.PLATFORM.weight > EnumTriageBlastRadius.REPO.weight
        assert EnumTriageBlastRadius.REPO.weight > EnumTriageBlastRadius.MODULE.weight
        assert EnumTriageBlastRadius.MODULE.weight > EnumTriageBlastRadius.LOCAL.weight


class TestRankScore:
    def test_severity_dominates_blast_radius(self) -> None:
        """A CRITICAL LOCAL finding must outrank a HIGH PLATFORM one only if severity*blast wins."""
        critical_local = _finding(
            severity=EnumTriageSeverity.CRITICAL,
            blast=EnumTriageBlastRadius.LOCAL,
        )
        high_platform = _finding(
            severity=EnumTriageSeverity.HIGH,
            blast=EnumTriageBlastRadius.PLATFORM,
        )
        assert critical_local.rank_score == 500 * 1 + 40
        assert high_platform.rank_score == 400 * 4 + 40
        assert high_platform.rank_score > critical_local.rank_score

    def test_freshness_breaks_severity_ties(self) -> None:
        """Same severity and blast, fresher evidence wins."""
        live = _finding(freshness=EnumTriageFreshness.LIVE)
        stale = _finding(freshness=EnumTriageFreshness.STALE)
        assert live.rank_score > stale.rank_score


class TestRankFindings:
    def test_descending_rank_score(self) -> None:
        findings = [
            _finding(severity=EnumTriageSeverity.LOW, probe="a"),
            _finding(severity=EnumTriageSeverity.CRITICAL, probe="b"),
            _finding(severity=EnumTriageSeverity.MEDIUM, probe="c"),
        ]
        ranked = rank_findings(findings)
        assert [f.severity for f in ranked] == [
            EnumTriageSeverity.CRITICAL,
            EnumTriageSeverity.MEDIUM,
            EnumTriageSeverity.LOW,
        ]

    def test_deterministic_tie_break(self) -> None:
        """Findings with identical rank sort by (probe_name, message) ascending."""
        a = _finding(probe="zeta", message="m1")
        b = _finding(probe="alpha", message="m1")
        c = _finding(probe="alpha", message="m0")
        ranked = rank_findings([a, b, c])
        assert ranked[0] == c
        assert ranked[1] == b
        assert ranked[2] == a

    def test_empty_input(self) -> None:
        assert rank_findings([]) == []


class TestModelTriageFinding:
    def test_frozen(self) -> None:
        f = _finding()
        with pytest.raises(ValidationError):
            f.message = "mutated"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelTriageFinding(
                source_probe="p",
                severity=EnumTriageSeverity.LOW,
                freshness=EnumTriageFreshness.LIVE,
                blast_radius=EnumTriageBlastRadius.LOCAL,
                message="m",
                unknown_field="x",  # type: ignore[call-arg]
            )


class TestModelProbeResult:
    def test_error_requires_message(self) -> None:
        with pytest.raises(ValidationError):
            ModelTriageProbeResult(
                probe_name="broken",
                status=EnumProbeStatus.ERROR,
                duration_ms=1200,
            )

    def test_timeout_requires_message(self) -> None:
        with pytest.raises(ValidationError):
            ModelTriageProbeResult(
                probe_name="slow",
                status=EnumProbeStatus.TIMEOUT,
                duration_ms=30000,
            )

    def test_error_with_message_accepted(self) -> None:
        result = ModelTriageProbeResult(
            probe_name="broken",
            status=EnumProbeStatus.ERROR,
            duration_ms=1200,
            error_message="connection refused",
        )
        assert result.error_message == "connection refused"

    def test_success_rejects_error_message(self) -> None:
        with pytest.raises(ValidationError):
            ModelTriageProbeResult(
                probe_name="ok",
                status=EnumProbeStatus.SUCCESS,
                duration_ms=50,
                error_message="should not be here",
            )

    def test_success_allows_empty_error(self) -> None:
        result = ModelTriageProbeResult(
            probe_name="ok",
            status=EnumProbeStatus.SUCCESS,
            duration_ms=50,
        )
        assert result.error_message == ""

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelTriageProbeResult(
                probe_name="x",
                status=EnumProbeStatus.SUCCESS,
                duration_ms=-1,
            )


class TestModelTriageReport:
    def test_severity_counts_tracks_ranked_findings(self) -> None:
        report = ModelTriageReport(
            run_id="test-run",
            ranked_findings=[
                _finding(severity=EnumTriageSeverity.CRITICAL),
                _finding(severity=EnumTriageSeverity.CRITICAL),
                _finding(severity=EnumTriageSeverity.LOW),
            ],
        )
        counts = report.severity_counts
        assert counts["CRITICAL"] == 2
        assert counts["LOW"] == 1
        assert counts["HIGH"] == 0

    def test_probe_status_counts(self) -> None:
        report = ModelTriageReport(
            run_id="test",
            probe_results=[
                ModelTriageProbeResult(
                    probe_name="p1",
                    status=EnumProbeStatus.SUCCESS,
                    duration_ms=10,
                ),
                ModelTriageProbeResult(
                    probe_name="p2",
                    status=EnumProbeStatus.ERROR,
                    duration_ms=5,
                    error_message="boom",
                ),
            ],
        )
        counts = report.probe_status_counts
        assert counts["SUCCESS"] == 1
        assert counts["ERROR"] == 1
        assert counts["TIMEOUT"] == 0

    def test_total_duration_ms(self) -> None:
        start = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)
        end = start + timedelta(seconds=1, milliseconds=500)
        report = ModelTriageReport(
            run_id="t",
            started_at=start,
            completed_at=end,
        )
        assert report.total_duration_ms == 1500

    def test_completed_before_started_rejected(self) -> None:
        start = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)
        end = start - timedelta(seconds=1)
        with pytest.raises(ValidationError):
            ModelTriageReport(
                run_id="t",
                started_at=start,
                completed_at=end,
            )

    def test_equal_timestamps_accepted(self) -> None:
        ts = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)
        report = ModelTriageReport(run_id="t", started_at=ts, completed_at=ts)
        assert report.total_duration_ms == 0
