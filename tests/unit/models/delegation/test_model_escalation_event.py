# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for ModelEscalationEvent and EnumQualityGateResult (OMN-10617)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_quality_gate_result import (
    EnumQualityGateResult,
)
from omnibase_core.models.delegation.model_escalation_event import ModelEscalationEvent
from omnibase_core.models.primitives.model_semver import ModelSemVer

_CORR_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
_SEMVER = ModelSemVer(major=1, minor=0, patch=0)

_VALID_KWARGS: dict = {
    "correlation_id": _CORR_ID,
    "prior_model": "qwen3-30b",
    "next_model": "claude-sonnet",
    "reason": "quality_score below threshold",
    "quality_gate_result": EnumQualityGateResult.FAIL_HEURISTIC,
    "attempt_number": 1,
    "max_attempts": 3,
    "contract_version": _SEMVER,
}


@pytest.mark.unit
class TestEnumQualityGateResult:
    def test_all_values_distinct(self) -> None:
        values = [e.value for e in EnumQualityGateResult]
        assert len(values) == len(set(values))

    def test_pass_value(self) -> None:
        assert EnumQualityGateResult.PASS.value == "pass"

    def test_fail_deterministic_value(self) -> None:
        assert EnumQualityGateResult.FAIL_DETERMINISTIC.value == "fail_deterministic"

    def test_fail_heuristic_value(self) -> None:
        assert EnumQualityGateResult.FAIL_HEURISTIC.value == "fail_heuristic"


@pytest.mark.unit
class TestModelEscalationEvent:
    def test_minimal_valid(self) -> None:
        event = ModelEscalationEvent(**_VALID_KWARGS)
        assert event.correlation_id == _CORR_ID
        assert event.prior_model == "qwen3-30b"
        assert event.next_model == "claude-sonnet"
        assert event.quality_gate_result is EnumQualityGateResult.FAIL_HEURISTIC
        assert event.attempt_number == 1
        assert event.max_attempts == 3
        assert event.contract_version == _SEMVER

    def test_frozen(self) -> None:
        event = ModelEscalationEvent(**_VALID_KWARGS)
        with pytest.raises(Exception):
            event.prior_model = "changed"  # type: ignore[misc]  # NOTE(OMN-10617): Intentional mutation to assert frozen-model enforcement.

    def test_attempt_number_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            ModelEscalationEvent(**{**_VALID_KWARGS, "attempt_number": 0})

    def test_max_attempts_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            ModelEscalationEvent(**{**_VALID_KWARGS, "max_attempts": 0})

    def test_attempt_number_exceeds_max_attempts_raises(self) -> None:
        with pytest.raises(ValidationError, match="must not exceed max_attempts"):
            ModelEscalationEvent(
                **{**_VALID_KWARGS, "attempt_number": 4, "max_attempts": 3}
            )

    def test_attempt_number_equals_max_attempts_is_valid(self) -> None:
        event = ModelEscalationEvent(
            **{**_VALID_KWARGS, "attempt_number": 3, "max_attempts": 3}
        )
        assert event.attempt_number == event.max_attempts

    def test_serialization_round_trip(self) -> None:
        event = ModelEscalationEvent(**_VALID_KWARGS)
        data = event.model_dump()
        restored = ModelEscalationEvent.model_validate(data)
        assert restored == event

    def test_json_round_trip(self) -> None:
        event = ModelEscalationEvent(**_VALID_KWARGS)
        json_str = event.model_dump_json()
        restored = ModelEscalationEvent.model_validate_json(json_str)
        assert restored == event

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelEscalationEvent(**{**_VALID_KWARGS, "unknown_field": "value"})

    def test_enum_coercion_from_string(self) -> None:
        data = {**_VALID_KWARGS, "quality_gate_result": "fail_deterministic"}
        event = ModelEscalationEvent.model_validate(data)
        assert event.quality_gate_result is EnumQualityGateResult.FAIL_DETERMINISTIC

    def test_pass_verdict_is_valid(self) -> None:
        event = ModelEscalationEvent(
            **{**_VALID_KWARGS, "quality_gate_result": EnumQualityGateResult.PASS}
        )
        assert event.quality_gate_result is EnumQualityGateResult.PASS
