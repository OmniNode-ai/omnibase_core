# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelSweepResult."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.telemetry.model_sweep_result import ModelSweepResult


def _make_sweep(**overrides: object) -> ModelSweepResult:
    defaults: dict[str, object] = {
        "sweep_type": "compliance",
        "session_id": "session-001",
        "correlation_id": "corr-001",
        "ran_at": datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC),
        "duration_seconds": 12.5,
        "passed": True,
        "summary": "All checks passed.",
    }
    defaults.update(overrides)
    return ModelSweepResult(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelSweepResult:
    def test_minimal_valid(self) -> None:
        result = _make_sweep()
        assert result.passed is True
        assert result.finding_count == 0
        assert result.critical_count == 0
        assert result.warning_count == 0
        assert result.repos_scanned == ()
        assert result.output_path is None
        assert result.schema_version == "1.0.0"

    def test_all_sweep_types_valid(self) -> None:
        for sweep_type in (
            "aislop",
            "coverage",
            "compliance",
            "contract",
            "dashboard",
            "runtime",
            "data_flow",
        ):
            r = _make_sweep(sweep_type=sweep_type)
            assert r.sweep_type == sweep_type

    def test_invalid_sweep_type(self) -> None:
        with pytest.raises(ValidationError):
            _make_sweep(sweep_type="unknown_sweep")

    def test_repos_scanned_tuple(self) -> None:
        result = _make_sweep(repos_scanned=("omnibase_core", "omnibase_infra"))
        assert result.repos_scanned == ("omnibase_core", "omnibase_infra")

    def test_with_output_path(self) -> None:
        result = _make_sweep(output_path="/tmp/sweep-output.json")
        assert result.output_path == "/tmp/sweep-output.json"

    def test_failed_with_findings(self) -> None:
        result = _make_sweep(
            passed=False,
            finding_count=5,
            critical_count=2,
            warning_count=3,
            summary="2 critical findings detected.",
        )
        assert result.passed is False
        assert result.finding_count == 5
        assert result.critical_count == 2
        assert result.warning_count == 3

    def test_frozen(self) -> None:
        result = _make_sweep()
        with pytest.raises(ValidationError):
            result.passed = False  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            _make_sweep(unknown_field="x")  # type: ignore[call-arg]
