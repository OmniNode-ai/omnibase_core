# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelProducerHealthStatus."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.event_bus.model_producer_health_status import (
    ModelProducerHealthStatus,
)


@pytest.mark.unit
class TestModelProducerHealthStatus:
    """Test suite for ModelProducerHealthStatus."""

    def test_initialization_with_required_fields(self):
        """Test initialization with required fields only."""
        status = ModelProducerHealthStatus(
            healthy=True,
            connected=True,
        )

        assert status.healthy is True
        assert status.connected is True
        assert status.latency_ms is None
        assert status.pending_messages == 0
        assert status.last_error is None
        assert status.last_error_timestamp is None
        assert status.messages_sent == 0
        assert status.messages_failed == 0
        assert status.broker_count == 0

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        status = ModelProducerHealthStatus(
            healthy=True,
            latency_ms=5.5,
            connected=True,
            pending_messages=10,
            last_error=None,
            last_error_timestamp=None,
            messages_sent=1000,
            messages_failed=5,
            broker_count=3,
        )

        assert status.healthy is True
        assert status.latency_ms == 5.5
        assert status.connected is True
        assert status.pending_messages == 10
        assert status.messages_sent == 1000
        assert status.messages_failed == 5
        assert status.broker_count == 3

    def test_initialization_unhealthy(self):
        """Test initialization for unhealthy status."""
        now = datetime.now(UTC)
        status = ModelProducerHealthStatus(
            healthy=False,
            connected=False,
            last_error="Connection refused",
            last_error_timestamp=now,
        )

        assert status.healthy is False
        assert status.connected is False
        assert status.last_error == "Connection refused"
        assert status.last_error_timestamp == now

    def test_immutability(self):
        """Test that model is immutable (frozen)."""
        status = ModelProducerHealthStatus(
            healthy=True,
            connected=True,
        )

        with pytest.raises(ValidationError):
            status.healthy = False

    def test_extra_forbid(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelProducerHealthStatus(
                healthy=True,
                connected=True,
                extra_field="not allowed",
            )

    def test_latency_ms_validation_negative(self):
        """Test latency_ms validation rejects negative values."""
        with pytest.raises(ValidationError):
            ModelProducerHealthStatus(healthy=True, connected=True, latency_ms=-1.0)

    def test_pending_messages_validation_negative(self):
        """Test pending_messages validation rejects negative values."""
        with pytest.raises(ValidationError):
            ModelProducerHealthStatus(healthy=True, connected=True, pending_messages=-1)

    def test_messages_sent_validation_negative(self):
        """Test messages_sent validation rejects negative values."""
        with pytest.raises(ValidationError):
            ModelProducerHealthStatus(healthy=True, connected=True, messages_sent=-1)

    def test_messages_failed_validation_negative(self):
        """Test messages_failed validation rejects negative values."""
        with pytest.raises(ValidationError):
            ModelProducerHealthStatus(healthy=True, connected=True, messages_failed=-1)

    def test_broker_count_validation_negative(self):
        """Test broker_count validation rejects negative values."""
        with pytest.raises(ValidationError):
            ModelProducerHealthStatus(healthy=True, connected=True, broker_count=-1)

    def test_last_error_strips_whitespace(self):
        """Test last_error strips whitespace."""
        status = ModelProducerHealthStatus(
            healthy=False,
            connected=False,
            last_error="  Error message  ",
        )
        assert status.last_error == "Error message"

    def test_last_error_empty_becomes_none(self):
        """Test empty last_error becomes None."""
        status = ModelProducerHealthStatus(
            healthy=False,
            connected=False,
            last_error="   ",
        )
        assert status.last_error is None

    def test_is_healthy(self):
        """Test is_healthy method."""
        healthy = ModelProducerHealthStatus(healthy=True, connected=True)
        unhealthy = ModelProducerHealthStatus(healthy=False, connected=False)

        assert healthy.is_healthy() is True
        assert unhealthy.is_healthy() is False

    def test_is_connected(self):
        """Test is_connected method."""
        connected = ModelProducerHealthStatus(healthy=True, connected=True)
        disconnected = ModelProducerHealthStatus(healthy=False, connected=False)

        assert connected.is_connected() is True
        assert disconnected.is_connected() is False

    def test_has_pending_messages(self):
        """Test has_pending_messages method."""
        with_pending = ModelProducerHealthStatus(
            healthy=True, connected=True, pending_messages=10
        )
        without_pending = ModelProducerHealthStatus(
            healthy=True, connected=True, pending_messages=0
        )

        assert with_pending.has_pending_messages() is True
        assert without_pending.has_pending_messages() is False

    def test_has_recent_error(self):
        """Test has_recent_error method."""
        with_error = ModelProducerHealthStatus(
            healthy=False, connected=False, last_error="Error"
        )
        without_error = ModelProducerHealthStatus(healthy=True, connected=True)

        assert with_error.has_recent_error() is True
        assert without_error.has_recent_error() is False

    def test_get_success_rate(self):
        """Test get_success_rate method."""
        # All successful
        all_success = ModelProducerHealthStatus(
            healthy=True, connected=True, messages_sent=100, messages_failed=0
        )
        assert all_success.get_success_rate() == 1.0

        # Some failures
        some_failures = ModelProducerHealthStatus(
            healthy=True, connected=True, messages_sent=90, messages_failed=10
        )
        assert some_failures.get_success_rate() == 0.9

        # All failures
        all_failures = ModelProducerHealthStatus(
            healthy=False, connected=True, messages_sent=0, messages_failed=100
        )
        assert all_failures.get_success_rate() == 0.0

        # No messages
        no_messages = ModelProducerHealthStatus(healthy=True, connected=True)
        assert no_messages.get_success_rate() == 1.0

    def test_get_failure_rate(self):
        """Test get_failure_rate method."""
        status = ModelProducerHealthStatus(
            healthy=True, connected=True, messages_sent=90, messages_failed=10
        )
        assert abs(status.get_failure_rate() - 0.1) < 1e-9

    def test_get_latency_category(self):
        """Test get_latency_category method."""
        # Excellent
        excellent = ModelProducerHealthStatus(
            healthy=True, connected=True, latency_ms=5.0
        )
        assert excellent.get_latency_category() == "excellent"

        # Good
        good = ModelProducerHealthStatus(healthy=True, connected=True, latency_ms=30.0)
        assert good.get_latency_category() == "good"

        # Acceptable
        acceptable = ModelProducerHealthStatus(
            healthy=True, connected=True, latency_ms=75.0
        )
        assert acceptable.get_latency_category() == "acceptable"

        # Slow
        slow = ModelProducerHealthStatus(healthy=True, connected=True, latency_ms=200.0)
        assert slow.get_latency_category() == "slow"

        # Very slow
        very_slow = ModelProducerHealthStatus(
            healthy=True, connected=True, latency_ms=600.0
        )
        assert very_slow.get_latency_category() == "very_slow"

        # Unknown
        unknown = ModelProducerHealthStatus(healthy=True, connected=True)
        assert unknown.get_latency_category() == "unknown"

    def test_is_latency_concerning(self):
        """Test is_latency_concerning method."""
        concerning = ModelProducerHealthStatus(
            healthy=True, connected=True, latency_ms=200.0
        )
        not_concerning = ModelProducerHealthStatus(
            healthy=True, connected=True, latency_ms=30.0
        )

        assert concerning.is_latency_concerning() is True
        assert not_concerning.is_latency_concerning() is False

    def test_get_health_summary(self):
        """Test get_health_summary method."""
        healthy = ModelProducerHealthStatus(
            healthy=True,
            connected=True,
            pending_messages=5,
            messages_sent=100,
        )

        summary = healthy.get_health_summary()
        assert "HEALTHY" in summary
        assert "connected" in summary
        assert "pending=5" in summary

        unhealthy = ModelProducerHealthStatus(
            healthy=False,
            connected=False,
        )

        summary = unhealthy.get_health_summary()
        assert "UNHEALTHY" in summary
        assert "disconnected" in summary

    def test_needs_attention(self):
        """Test needs_attention method."""
        # Unhealthy
        unhealthy = ModelProducerHealthStatus(healthy=False, connected=True)
        assert unhealthy.needs_attention() is True

        # Disconnected
        disconnected = ModelProducerHealthStatus(healthy=True, connected=False)
        assert disconnected.needs_attention() is True

        # Many pending messages
        many_pending = ModelProducerHealthStatus(
            healthy=True, connected=True, pending_messages=1001
        )
        assert many_pending.needs_attention() is True

        # High failure rate
        high_failures = ModelProducerHealthStatus(
            healthy=True, connected=True, messages_sent=80, messages_failed=20
        )
        assert high_failures.needs_attention() is True

        # High latency
        high_latency = ModelProducerHealthStatus(
            healthy=True, connected=True, latency_ms=200.0
        )
        assert high_latency.needs_attention() is True

        # All good
        all_good = ModelProducerHealthStatus(
            healthy=True,
            connected=True,
            latency_ms=5.0,
            pending_messages=10,
            messages_sent=1000,
            messages_failed=5,
        )
        assert all_good.needs_attention() is False

    def test_get_status_dict(self):
        """Test get_status_dict method."""
        status = ModelProducerHealthStatus(
            healthy=True,
            connected=True,
            latency_ms=5.0,
            pending_messages=5,
            messages_sent=100,
            messages_failed=2,
            broker_count=3,
        )

        result = status.get_status_dict()

        assert result["healthy"] is True
        assert result["connected"] is True
        assert result["latency_ms"] == 5.0
        assert result["latency_category"] == "excellent"
        assert result["pending_messages"] == 5
        assert result["messages_sent"] == 100
        assert result["messages_failed"] == 2
        assert result["broker_count"] == 3
        assert result["has_error"] is False
        assert result["needs_attention"] is False

    def test_create_healthy_factory(self):
        """Test create_healthy factory method."""
        status = ModelProducerHealthStatus.create_healthy()

        assert status.healthy is True
        assert status.connected is True
        assert status.last_error is None
        assert status.messages_failed == 0
        assert status.broker_count == 1

    def test_create_healthy_with_params(self):
        """Test create_healthy with parameters."""
        status = ModelProducerHealthStatus.create_healthy(
            latency_ms=5.0,
            pending_messages=10,
            messages_sent=100,
            broker_count=3,
        )

        assert status.latency_ms == 5.0
        assert status.pending_messages == 10
        assert status.messages_sent == 100
        assert status.broker_count == 3

    def test_create_unhealthy_factory(self):
        """Test create_unhealthy factory method."""
        status = ModelProducerHealthStatus.create_unhealthy(
            error_message="Connection timeout"
        )

        assert status.healthy is False
        assert status.connected is False
        assert status.last_error == "Connection timeout"
        assert status.last_error_timestamp is not None

    def test_create_unhealthy_with_params(self):
        """Test create_unhealthy with parameters."""
        status = ModelProducerHealthStatus.create_unhealthy(
            error_message="Error",
            connected=True,
            pending_messages=100,
            messages_sent=50,
            messages_failed=10,
        )

        assert status.connected is True
        assert status.pending_messages == 100
        assert status.messages_sent == 50
        assert status.messages_failed == 10

    def test_create_disconnected_factory(self):
        """Test create_disconnected factory method."""
        status = ModelProducerHealthStatus.create_disconnected()

        assert status.healthy is False
        assert status.connected is False
        assert status.broker_count == 0
        assert "disconnected" in status.last_error.lower()

    def test_create_disconnected_with_error(self):
        """Test create_disconnected with custom error."""
        status = ModelProducerHealthStatus.create_disconnected(
            error_message="Network unreachable"
        )

        assert status.last_error == "Network unreachable"

    def test_serialization(self):
        """Test model serialization."""
        status = ModelProducerHealthStatus(
            healthy=True,
            latency_ms=5.5,
            connected=True,
            pending_messages=10,
            messages_sent=100,
            messages_failed=2,
            broker_count=3,
        )

        data = status.model_dump()

        assert data["healthy"] is True
        assert data["latency_ms"] == 5.5
        assert data["connected"] is True
        assert data["pending_messages"] == 10
        assert data["messages_sent"] == 100
        assert data["messages_failed"] == 2
        assert data["broker_count"] == 3

    def test_deserialization(self):
        """Test model deserialization from dict."""
        data = {
            "healthy": True,
            "connected": True,
            "latency_ms": 10.0,
            "pending_messages": 5,
        }

        status = ModelProducerHealthStatus(**data)

        assert status.healthy is True
        assert status.connected is True
        assert status.latency_ms == 10.0
        assert status.pending_messages == 5
