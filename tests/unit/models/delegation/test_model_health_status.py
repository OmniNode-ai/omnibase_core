# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for ModelModelHealthStatus and EnumModelHealthState (OMN-10611)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_model_health_state import EnumModelHealthState
from omnibase_core.models.delegation.model_model_health_status import (
    ModelModelHealthStatus,
)

_ENDPOINT = "http://192.168.86.201:8000"
_NOW = datetime(2026, 5, 6, 10, 0, 0, tzinfo=UTC)


@pytest.mark.unit
class TestEnumModelHealthState:
    def test_all_values_present(self) -> None:
        assert EnumModelHealthState.AVAILABLE == "available"
        assert EnumModelHealthState.DEGRADED == "degraded"
        assert EnumModelHealthState.UNAVAILABLE == "unavailable"

    def test_exactly_three_members(self) -> None:
        assert len(EnumModelHealthState) == 3

    def test_str_coercible(self) -> None:
        assert str(EnumModelHealthState.AVAILABLE) == "available"


@pytest.mark.unit
class TestModelModelHealthStatus:
    def test_available_state(self) -> None:
        status = ModelModelHealthStatus(
            model_key="qwen3-coder",
            endpoint_url=_ENDPOINT,
            state=EnumModelHealthState.AVAILABLE,
            latency_ms=120.5,
            last_checked_at=_NOW,
        )
        assert status.state is EnumModelHealthState.AVAILABLE
        assert status.latency_ms == 120.5
        assert status.consecutive_failures == 0
        assert status.error_message is None

    def test_degraded_state(self) -> None:
        status = ModelModelHealthStatus(
            model_key="qwen3-coder",
            endpoint_url=_ENDPOINT,
            state=EnumModelHealthState.DEGRADED,
            latency_ms=6000.0,
            last_checked_at=_NOW,
        )
        assert status.state is EnumModelHealthState.DEGRADED
        assert (
            status.latency_ms is not None
            and status.latency_ms > status.latency_threshold_ms
        )

    def test_unavailable_state(self) -> None:
        status = ModelModelHealthStatus(
            model_key="qwen3-coder",
            endpoint_url=_ENDPOINT,
            state=EnumModelHealthState.UNAVAILABLE,
            error_message="connection refused",
            consecutive_failures=3,
            last_checked_at=_NOW,
        )
        assert status.state is EnumModelHealthState.UNAVAILABLE
        assert status.error_message == "connection refused"
        assert status.consecutive_failures == 3

    def test_default_latency_threshold(self) -> None:
        status = ModelModelHealthStatus(
            model_key="qwen3-coder",
            endpoint_url=_ENDPOINT,
            state=EnumModelHealthState.AVAILABLE,
            last_checked_at=_NOW,
        )
        assert status.latency_threshold_ms == 5000.0

    def test_frozen(self) -> None:
        status = ModelModelHealthStatus(
            model_key="qwen3-coder",
            endpoint_url=_ENDPOINT,
            state=EnumModelHealthState.AVAILABLE,
            last_checked_at=_NOW,
        )
        with pytest.raises(Exception):
            status.state = EnumModelHealthState.UNAVAILABLE  # NOTE(OMN-10611): intentional mutation attempt to verify frozen model behavior.  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelModelHealthStatus.model_validate(
                {
                    "model_key": "qwen3-coder",
                    "endpoint_url": _ENDPOINT,
                    "state": "available",
                    "unknown_field": "bad",
                    "last_checked_at": _NOW,
                }
            )

    def test_invalid_state_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelModelHealthStatus(
                model_key="qwen3-coder",
                endpoint_url=_ENDPOINT,
                state="flying",  # NOTE(OMN-10611): intentional invalid enum value for validation-path testing.  # type: ignore[arg-type]
                last_checked_at=_NOW,
            )

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("latency_ms", -1.0),
            ("latency_threshold_ms", -1.0),
            ("consecutive_failures", -1),
        ],
    )
    def test_negative_health_metrics_raise(
        self,
        field_name: str,
        value: float | int,
    ) -> None:
        payload = {
            "model_key": "qwen3-coder",
            "endpoint_url": _ENDPOINT,
            "state": EnumModelHealthState.AVAILABLE,
            "last_checked_at": _NOW,
            field_name: value,
        }
        with pytest.raises(ValidationError):
            ModelModelHealthStatus(**payload)

    def test_serialization_round_trip(self) -> None:
        status = ModelModelHealthStatus(
            model_key="qwen3-coder",
            endpoint_url=_ENDPOINT,
            state=EnumModelHealthState.DEGRADED,
            latency_ms=7500.0,
            consecutive_failures=1,
            error_message=None,
            last_checked_at=_NOW,
        )
        raw = json.loads(status.model_dump_json())
        restored = ModelModelHealthStatus.model_validate(raw)
        assert restored.state is EnumModelHealthState.DEGRADED
        assert restored.latency_ms == status.latency_ms
        assert restored.consecutive_failures == status.consecutive_failures

    def test_last_checked_at_defaults_to_now(self) -> None:
        before = datetime.now(UTC)
        status = ModelModelHealthStatus(
            model_key="qwen3-coder",
            endpoint_url=_ENDPOINT,
            state=EnumModelHealthState.AVAILABLE,
        )
        after = datetime.now(UTC)
        assert before <= status.last_checked_at <= after
