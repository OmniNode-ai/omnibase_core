"""
Tests for ModelCircuitBreaker.

Comprehensive tests for circuit breaker configuration and state management.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker


@pytest.mark.unit
class TestModelCircuitBreakerInitialization:
    """Test ModelCircuitBreaker initialization."""

    def test_create_default_circuit_breaker(self):
        """Test creating a circuit breaker with default values."""
        cb = ModelCircuitBreaker()
        assert cb is not None
        assert isinstance(cb, ModelCircuitBreaker)
        assert cb.enabled is True
        assert cb.state == EnumCircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_circuit_breaker_with_custom_values(self):
        """Test creating circuit breaker with custom values."""
        cb = ModelCircuitBreaker(
            enabled=False,
            failure_threshold=10,
            success_threshold=5,
            timeout_seconds=120,
        )
        assert cb.enabled is False
        assert cb.failure_threshold == 10
        assert cb.success_threshold == 5
        assert cb.timeout_seconds == 120

    def test_circuit_breaker_inheritance(self):
        """Test that ModelCircuitBreaker inherits from BaseModel."""
        from pydantic import BaseModel

        cb = ModelCircuitBreaker()
        assert isinstance(cb, BaseModel)


@pytest.mark.unit
class TestModelCircuitBreakerValidation:
    """Test ModelCircuitBreaker field validation."""

    def test_failure_threshold_validation(self):
        """Test failure_threshold field constraints."""
        # Valid values
        cb = ModelCircuitBreaker(failure_threshold=1)
        assert cb.failure_threshold == 1

        cb = ModelCircuitBreaker(failure_threshold=100)
        assert cb.failure_threshold == 100

        # Invalid values
        with pytest.raises(ValueError):
            ModelCircuitBreaker(failure_threshold=0)

        with pytest.raises(ValueError):
            ModelCircuitBreaker(failure_threshold=101)

    def test_success_threshold_validation(self):
        """Test success_threshold field constraints."""
        # Valid values
        cb = ModelCircuitBreaker(success_threshold=1)
        assert cb.success_threshold == 1

        cb = ModelCircuitBreaker(success_threshold=20)
        assert cb.success_threshold == 20

        # Invalid values
        with pytest.raises(ValueError):
            ModelCircuitBreaker(success_threshold=0)

        with pytest.raises(ValueError):
            ModelCircuitBreaker(success_threshold=21)

    def test_timeout_seconds_validation(self):
        """Test timeout_seconds field constraints."""
        # Valid values
        cb = ModelCircuitBreaker(timeout_seconds=10)
        assert cb.timeout_seconds == 10

        cb = ModelCircuitBreaker(timeout_seconds=3600)
        assert cb.timeout_seconds == 3600

        # Invalid values
        with pytest.raises(ValueError):
            ModelCircuitBreaker(timeout_seconds=9)

        with pytest.raises(ValueError):
            ModelCircuitBreaker(timeout_seconds=3601)

    def test_state_pattern_validation(self):
        """Test state field pattern validation."""
        # Valid states - strings are coerced to enum values
        state_mapping = {
            "closed": EnumCircuitBreakerState.CLOSED,
            "open": EnumCircuitBreakerState.OPEN,
            "half_open": EnumCircuitBreakerState.HALF_OPEN,
        }
        for state_str, expected_enum in state_mapping.items():
            cb = ModelCircuitBreaker(state=state_str)
            assert cb.state == expected_enum

        # Invalid state
        with pytest.raises(ValueError):
            ModelCircuitBreaker(state="invalid_state")

    def test_failure_rate_threshold_validation(self):
        """Test failure_rate_threshold field constraints."""
        # Valid values
        cb = ModelCircuitBreaker(failure_rate_threshold=0.0)
        assert cb.failure_rate_threshold == 0.0

        cb = ModelCircuitBreaker(failure_rate_threshold=1.0)
        assert cb.failure_rate_threshold == 1.0

        # Invalid values
        with pytest.raises(ValueError):
            ModelCircuitBreaker(failure_rate_threshold=-0.1)

        with pytest.raises(ValueError):
            ModelCircuitBreaker(failure_rate_threshold=1.1)


@pytest.mark.unit
class TestModelCircuitBreakerSerialization:
    """Test ModelCircuitBreaker serialization."""

    def test_circuit_breaker_serialization(self):
        """Test circuit breaker model_dump."""
        cb = ModelCircuitBreaker(
            failure_threshold=10,
            success_threshold=5,
        )
        data = cb.model_dump()
        assert isinstance(data, dict)
        assert data["failure_threshold"] == 10
        assert data["success_threshold"] == 5
        assert data["enabled"] is True

    def test_circuit_breaker_deserialization(self):
        """Test circuit breaker model_validate."""
        data = {
            "failure_threshold": 10,
            "success_threshold": 5,
            "timeout_seconds": 120,
        }
        cb = ModelCircuitBreaker.model_validate(data)
        assert cb.failure_threshold == 10
        assert cb.success_threshold == 5
        assert cb.timeout_seconds == 120

    def test_circuit_breaker_json_serialization(self):
        """Test circuit breaker JSON serialization."""
        cb = ModelCircuitBreaker()
        json_data = cb.model_dump_json()
        assert isinstance(json_data, str)
        assert "failure_threshold" in json_data

    def test_circuit_breaker_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelCircuitBreaker(
            failure_threshold=15,
            success_threshold=7,
            timeout_seconds=90,
        )
        data = original.model_dump()
        restored = ModelCircuitBreaker.model_validate(data)
        assert restored.failure_threshold == original.failure_threshold
        assert restored.success_threshold == original.success_threshold
        assert restored.timeout_seconds == original.timeout_seconds


@pytest.mark.unit
class TestModelCircuitBreakerStateManagement:
    """Test circuit breaker state management."""

    def test_should_allow_request_when_disabled(self):
        """Test that disabled circuit breaker allows all requests."""
        cb = ModelCircuitBreaker(enabled=False)
        assert cb.should_allow_request() is True

    def test_should_allow_request_when_closed(self):
        """Test that closed circuit breaker allows requests."""
        cb = ModelCircuitBreaker(state="closed")
        assert cb.should_allow_request() is True

    def test_should_deny_request_when_open(self):
        """Test that open circuit breaker denies requests."""
        cb = ModelCircuitBreaker(
            state="open",
            last_state_change=datetime.now(UTC),  # Recent state change
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            assert cb.should_allow_request() is False

    def test_should_allow_limited_requests_when_half_open(self):
        """Test that half-open circuit breaker allows limited requests."""
        cb = ModelCircuitBreaker(
            state="half_open",
            half_open_max_requests=3,
            half_open_requests=0,
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            assert cb.should_allow_request() is True
            cb.half_open_requests = 3
            assert cb.should_allow_request() is False


@pytest.mark.unit
class TestModelCircuitBreakerFailureTracking:
    """Test circuit breaker failure tracking."""

    def test_record_success(self):
        """Test recording successful requests."""
        cb = ModelCircuitBreaker(state="half_open", success_count=0)
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.record_success()
            assert cb.total_requests == 1

    def test_record_failure(self):
        """Test recording failed requests."""
        cb = ModelCircuitBreaker(failure_count=0)
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.record_failure()
            assert cb.failure_count == 1
            assert cb.total_requests == 1
            assert cb.last_failure_time is not None

    def test_record_slow_call(self):
        """Test recording slow calls."""
        cb = ModelCircuitBreaker(
            slow_call_duration_threshold_ms=1000,
            failure_count=0,
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.record_slow_call(1500)
            assert cb.failure_count == 1

    def test_record_slow_call_below_threshold(self):
        """Test that slow calls below threshold don't trigger failure."""
        cb = ModelCircuitBreaker(
            slow_call_duration_threshold_ms=1000,
            failure_count=0,
        )
        cb.record_slow_call(500)
        assert cb.failure_count == 0

    def test_get_failure_rate(self):
        """Test failure rate calculation."""
        cb = ModelCircuitBreaker(failure_count=5, total_requests=10)
        assert cb.get_failure_rate() == 0.5

        cb = ModelCircuitBreaker(failure_count=0, total_requests=0)
        assert cb.get_failure_rate() == 0.0


@pytest.mark.unit
class TestModelCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions."""

    def test_transition_to_open_on_threshold(self):
        """Test transition to open state when threshold reached."""
        cb = ModelCircuitBreaker(
            state="closed",
            failure_threshold=5,
            failure_count=0,
            total_requests=0,
            minimum_request_threshold=5,
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            # Record enough failures to trigger open
            for _ in range(5):
                cb.record_failure()
            assert cb.state == EnumCircuitBreakerState.OPEN

    def test_transition_to_half_open_after_timeout(self):
        """Test transition from open to half-open after timeout."""
        past_time = datetime.now(UTC) - timedelta(seconds=120)
        cb = ModelCircuitBreaker(
            state="open",
            timeout_seconds=60,
            last_state_change=past_time,
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            state = cb.get_current_state()
            assert state == "half_open"

    def test_transition_to_closed_on_success(self):
        """Test transition from half-open to closed on success."""
        cb = ModelCircuitBreaker(
            state="half_open",
            success_threshold=3,
            success_count=0,
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            for _ in range(3):
                cb.record_success()
            assert cb.state == EnumCircuitBreakerState.CLOSED

    def test_transition_back_to_open_on_half_open_failure(self):
        """Test transition back to open on failure in half-open state."""
        cb = ModelCircuitBreaker(state="half_open")
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.record_failure()
            assert cb.state == EnumCircuitBreakerState.OPEN


@pytest.mark.unit
class TestModelCircuitBreakerManualControl:
    """Test circuit breaker manual control methods."""

    def test_force_open(self):
        """Test forcing circuit breaker to open state."""
        cb = ModelCircuitBreaker(state="closed")
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.force_open()
            assert cb.state == EnumCircuitBreakerState.OPEN

    def test_force_close(self):
        """Test forcing circuit breaker to closed state."""
        cb = ModelCircuitBreaker(state="open")
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.force_close()
            assert cb.state == EnumCircuitBreakerState.CLOSED

    def test_reset_state(self):
        """Test resetting circuit breaker to initial state."""
        cb = ModelCircuitBreaker(
            state="open",
            failure_count=10,
            success_count=5,
            total_requests=15,
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.reset_state()
            assert cb.state == EnumCircuitBreakerState.CLOSED
            assert cb.failure_count == 0
            assert cb.success_count == 0
            assert cb.total_requests == 0


@pytest.mark.unit
class TestModelCircuitBreakerFactoryMethods:
    """Test circuit breaker factory methods."""

    def test_create_fast_fail(self):
        """Test creating fast-fail circuit breaker."""
        cb = ModelCircuitBreaker.create_fast_fail()
        assert cb.enabled is True
        assert cb.failure_threshold == 3
        assert cb.success_threshold == 2
        assert cb.timeout_seconds == 30
        assert cb.failure_rate_threshold == 0.3

    def test_create_resilient(self):
        """Test creating resilient circuit breaker."""
        cb = ModelCircuitBreaker.create_resilient()
        assert cb.enabled is True
        assert cb.failure_threshold == 10
        assert cb.success_threshold == 5
        assert cb.timeout_seconds == 120
        assert cb.failure_rate_threshold == 0.6

    def test_create_disabled(self):
        """Test creating disabled circuit breaker."""
        cb = ModelCircuitBreaker.create_disabled()
        assert cb.enabled is False


@pytest.mark.unit
class TestModelCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases."""

    def test_cleanup_old_data(self):
        """Test cleanup of old failure data outside window."""
        past_time = datetime.now(UTC) - timedelta(seconds=200)
        cb = ModelCircuitBreaker(
            window_size_seconds=120,
            failure_count=10,
            total_requests=15,
            last_failure_time=past_time,
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.record_success()
            # Counters should be reset as last failure was outside window
            assert cb.failure_count == 0
            # After cleanup, total_requests is also reset to 0 by _cleanup_old_data
            assert cb.total_requests == 0

    def test_minimum_request_threshold(self):
        """Test that circuit doesn't open below minimum requests."""
        cb = ModelCircuitBreaker(
            failure_threshold=5,
            minimum_request_threshold=10,
            failure_count=5,
            total_requests=5,
        )
        assert cb._should_open_circuit() is False

        cb.total_requests = 10
        assert cb._should_open_circuit() is True

    def test_get_current_state_when_disabled(self):
        """Test get_current_state returns 'disabled' when disabled."""
        cb = ModelCircuitBreaker(enabled=False)
        assert cb.get_current_state() == "disabled"

    def test_record_success_when_disabled(self):
        """Test that recording success when disabled has no effect."""
        cb = ModelCircuitBreaker(enabled=False, total_requests=0)
        cb.record_success()
        assert cb.total_requests == 0

    def test_record_failure_when_disabled(self):
        """Test that recording failure when disabled has no effect."""
        cb = ModelCircuitBreaker(enabled=False, failure_count=0)
        cb.record_failure()
        assert cb.failure_count == 0

    def test_slow_call_when_disabled(self):
        """Test that slow calls when disabled have no effect."""
        cb = ModelCircuitBreaker(
            enabled=False,
            slow_call_duration_threshold_ms=1000,
            failure_count=0,
        )
        cb.record_slow_call(2000)
        assert cb.failure_count == 0

    def test_slow_call_without_threshold(self):
        """Test that slow calls without threshold have no effect."""
        cb = ModelCircuitBreaker(
            slow_call_duration_threshold_ms=None,
            failure_count=0,
        )
        with patch(
            "omnibase_core.models.configuration.model_circuit_breaker.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            cb.record_slow_call(2000)
            assert cb.failure_count == 0


@pytest.mark.unit
class TestModelCircuitBreakerAttributes:
    """Test circuit breaker attributes and metadata."""

    def test_circuit_breaker_attributes(self):
        """Test that circuit breaker has expected attributes."""
        cb = ModelCircuitBreaker()
        assert hasattr(cb, "model_dump")
        assert callable(cb.model_dump)
        assert hasattr(ModelCircuitBreaker, "model_validate")
        assert callable(ModelCircuitBreaker.model_validate)

    def test_circuit_breaker_docstring(self):
        """Test circuit breaker docstring."""
        assert ModelCircuitBreaker.__doc__ is not None
        assert "circuit breaker" in ModelCircuitBreaker.__doc__.lower()

    def test_circuit_breaker_class_name(self):
        """Test circuit breaker class name."""
        assert ModelCircuitBreaker.__name__ == "ModelCircuitBreaker"

    def test_circuit_breaker_module(self):
        """Test circuit breaker module."""
        assert (
            ModelCircuitBreaker.__module__
            == "omnibase_core.models.configuration.model_circuit_breaker"
        )

    def test_circuit_breaker_copy(self):
        """Test circuit breaker copying."""
        cb = ModelCircuitBreaker(failure_threshold=10)
        copied = cb.model_copy()
        assert copied is not None
        assert copied.failure_threshold == 10
        assert copied is not cb
