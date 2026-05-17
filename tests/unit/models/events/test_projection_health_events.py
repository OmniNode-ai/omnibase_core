# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelProjectionDegradedEvent and ModelProjectionRecoveredEvent — OMN-11193."""

from datetime import UTC, datetime

import pytest


@pytest.mark.unit
def test_model_projection_degraded_event_create() -> None:
    from omnibase_core.models.events.model_projection_degraded_event import (
        ModelProjectionDegradedEvent,
    )

    now = datetime.now(UTC)
    event = ModelProjectionDegradedEvent(
        projection_name="dashboard_metrics",
        sla_seconds=60,
        actual_staleness_seconds=90.5,
        degraded_behavior="serve_stale_with_warning",
        observed_at=now,
        source_contract_hash="abc123def456",
    )
    assert event.projection_name == "dashboard_metrics"
    assert event.sla_seconds == 60
    assert event.actual_staleness_seconds == 90.5
    assert event.degraded_behavior == "serve_stale_with_warning"
    assert event.observed_at == now
    assert event.source_contract_hash == "abc123def456"


@pytest.mark.unit
def test_model_projection_degraded_event_frozen() -> None:
    from omnibase_core.models.events.model_projection_degraded_event import (
        ModelProjectionDegradedEvent,
    )

    event = ModelProjectionDegradedEvent(
        projection_name="node_registry",
        sla_seconds=30,
        actual_staleness_seconds=45.0,
        degraded_behavior="block_reads",
        observed_at=datetime.now(UTC),
        source_contract_hash="deadbeef",
    )
    with pytest.raises(Exception):
        event.projection_name = "other"  # type: ignore[misc]


@pytest.mark.unit
def test_model_projection_recovered_event_create() -> None:
    from omnibase_core.models.events.model_projection_recovered_event import (
        ModelProjectionRecoveredEvent,
    )

    now = datetime.now(UTC)
    event = ModelProjectionRecoveredEvent(
        projection_name="dashboard_metrics",
        recovered_at=now,
        recovery_staleness_seconds=5.2,
        source_contract_hash="abc123def456",
    )
    assert event.projection_name == "dashboard_metrics"
    assert event.recovered_at == now
    assert event.recovery_staleness_seconds == 5.2
    assert event.source_contract_hash == "abc123def456"


@pytest.mark.unit
def test_model_projection_recovered_event_frozen() -> None:
    from omnibase_core.models.events.model_projection_recovered_event import (
        ModelProjectionRecoveredEvent,
    )

    event = ModelProjectionRecoveredEvent(
        projection_name="node_registry",
        recovered_at=datetime.now(UTC),
        recovery_staleness_seconds=1.0,
        source_contract_hash="cafebabe",
    )
    with pytest.raises(Exception):
        event.projection_name = "other"  # type: ignore[misc]
