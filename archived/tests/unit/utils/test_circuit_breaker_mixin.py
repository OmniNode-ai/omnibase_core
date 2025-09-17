#!/usr/bin/env python3
"""
Unit tests for CircuitBreakerMixin.

Tests the circuit breaker mixin functionality including thread safety,
configuration management, and fault tolerance patterns.
"""

import asyncio
import threading
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.resilience.circuit_breaker import (
    CircuitBreakerState,
    ModelCircuitBreakerConfig,
)
from omnibase_core.utils.circuit_breaker_mixin import (
    CircuitBreakerMixin,
    create_default_circuit_breaker_config,
    create_lenient_circuit_breaker_config,
    create_strict_circuit_breaker_config,
)


class TestableCircuitBreakerMixin(CircuitBreakerMixin):
    """Test implementation of CircuitBreakerMixin for testing."""

    def __init__(self):
        # Initialize as if called by multiple inheritance
        super().__init__()


class TestCircuitBreakerMixin:
    """Test suite for CircuitBreakerMixin."""

    def test_basic_initialization(self):
        """Test basic mixin initialization."""
        mixin = TestableCircuitBreakerMixin()

        assert hasattr(mixin, "_circuit_breakers")
        assert hasattr(mixin, "_circuit_breaker_configs")
        assert hasattr(mixin, "_circuit_breaker_lock")
        assert len(mixin._circuit_breakers) == 0
        assert len(mixin._circuit_breaker_configs) == 0
        assert isinstance(mixin._circuit_breaker_lock, type(threading.RLock()))

    def test_setup_circuit_breakers(self):
        """Test circuit breaker setup with configurations."""
        mixin = TestableCircuitBreakerMixin()

        configs = {
            "service_a": ModelCircuitBreakerConfig(
                failure_threshold=3, recovery_timeout_seconds=20
            ),
            "service_b": ModelCircuitBreakerConfig(
                failure_threshold=5, recovery_timeout_seconds=30
            ),
        }

        mixin._setup_circuit_breakers(configs)

        assert len(mixin._circuit_breakers) == 2
        assert len(mixin._circuit_breaker_configs) == 2
        assert "service_a" in mixin._circuit_breakers
        assert "service_b" in mixin._circuit_breakers

    def test_get_circuit_breaker_existing(self):
        """Test getting existing circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        config = ModelCircuitBreakerConfig()
        configs = {"test_service": config}
        mixin._setup_circuit_breakers(configs)

        breaker = mixin._get_circuit_breaker("test_service")

        assert breaker is not None
        assert breaker.service_name == "test_service"

    def test_get_circuit_breaker_auto_create_with_config(self):
        """Test automatic circuit breaker creation with existing config."""
        mixin = TestableCircuitBreakerMixin()

        # Set up config without creating breaker
        config = ModelCircuitBreakerConfig(failure_threshold=7)
        mixin._circuit_breaker_configs["new_service"] = config

        breaker = mixin._get_circuit_breaker("new_service")

        assert breaker is not None
        assert breaker.service_name == "new_service"
        assert "new_service" in mixin._circuit_breakers

    def test_get_circuit_breaker_auto_create_with_default(self):
        """Test automatic circuit breaker creation with default config."""
        mixin = TestableCircuitBreakerMixin()

        breaker = mixin._get_circuit_breaker("unknown_service")

        assert breaker is not None
        assert breaker.service_name == "unknown_service"
        assert "unknown_service" in mixin._circuit_breakers
        assert "unknown_service" in mixin._circuit_breaker_configs

    @pytest.mark.asyncio
    async def test_call_with_circuit_breaker_success(self):
        """Test successful function call through circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        async def test_function(value):
            return f"success_{value}"

        result = await mixin._call_with_circuit_breaker(
            "test_service", test_function, "test_input"
        )

        assert result == "success_test_input"

    @pytest.mark.asyncio
    async def test_call_with_circuit_breaker_onex_error_passthrough(self):
        """Test that OnexError is passed through unchanged."""
        mixin = TestableCircuitBreakerMixin()

        async def failing_function():
            raise OnexError(
                message="Test error", error_code=CoreErrorCode.VALIDATION_FAILED
            )

        with pytest.raises(OnexError) as exc_info:
            await mixin._call_with_circuit_breaker("test_service", failing_function)

        assert exc_info.value.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "Test error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_with_circuit_breaker_generic_error_wrapping(self):
        """Test that generic exceptions are wrapped in OnexError."""
        mixin = TestableCircuitBreakerMixin()

        async def failing_function():
            raise ValueError("Generic error")

        with pytest.raises(OnexError) as exc_info:
            await mixin._call_with_circuit_breaker("test_service", failing_function)

        assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED
        assert "Service call failed: test_service" in exc_info.value.message
        # The context might be nested, let's check the actual structure
        context_data = exc_info.value.context.get("context", exc_info.value.context)
        assert "Generic error" in str(context_data.get("original_error", ""))

    def test_get_circuit_breaker_state_existing(self):
        """Test getting state of existing circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        # Mock circuit breaker
        mock_breaker = Mock()
        mock_breaker.get_state.return_value = CircuitBreakerState.CLOSED
        mixin._circuit_breakers["test_service"] = mock_breaker

        state = mixin._get_circuit_breaker_state("test_service")

        assert state == CircuitBreakerState.CLOSED
        mock_breaker.get_state.assert_called_once()

    def test_get_circuit_breaker_state_nonexistent(self):
        """Test getting state of non-existent circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        state = mixin._get_circuit_breaker_state("nonexistent_service")

        assert state == CircuitBreakerState.CLOSED

    def test_get_circuit_breaker_metrics_existing(self):
        """Test getting metrics for existing circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        # Mock circuit breaker and metrics
        mock_metrics = Mock()
        mock_metrics.current_state = CircuitBreakerState.HALF_OPEN
        mock_metrics.failed_requests = 3
        mock_metrics.successful_requests = 7
        mock_metrics.total_requests = 10
        mock_metrics.last_failure_time = "2025-01-15T10:30:00Z"
        mock_metrics.last_success_time = "2025-01-15T10:35:00Z"
        mock_metrics.get_failure_rate.return_value = 0.3

        mock_breaker = Mock()
        mock_breaker.get_metrics.return_value = mock_metrics
        mock_breaker.config = ModelCircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout_seconds=30,
            request_timeout_seconds=10.0,
        )

        mixin._circuit_breakers["test_service"] = mock_breaker

        metrics = mixin._get_circuit_breaker_metrics("test_service")

        assert metrics["state"] == "half_open"
        assert metrics["failure_count"] == 3
        assert metrics["success_count"] == 7
        assert metrics["total_requests"] == 10
        assert metrics["last_failure_time"] == "2025-01-15T10:30:00Z"
        assert metrics["last_success_time"] == "2025-01-15T10:35:00Z"
        assert metrics["failure_rate"] == 0.3
        assert metrics["config"]["failure_threshold"] == 5

    def test_get_circuit_breaker_metrics_nonexistent(self):
        """Test getting metrics for non-existent circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        metrics = mixin._get_circuit_breaker_metrics("nonexistent_service")

        assert metrics["state"] == "not_configured"
        assert metrics["failure_count"] == 0
        assert metrics["success_count"] == 0
        assert metrics["last_failure_time"] is None

    def test_configure_circuit_breaker(self):
        """Test configuring a circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        config = ModelCircuitBreakerConfig(
            failure_threshold=3, recovery_timeout_seconds=45
        )

        mixin._configure_circuit_breaker("new_service", config)

        assert "new_service" in mixin._circuit_breaker_configs
        assert "new_service" in mixin._circuit_breakers
        assert mixin._circuit_breaker_configs["new_service"] == config

    def test_remove_circuit_breaker(self):
        """Test removing a circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        # Setup circuit breaker
        config = ModelCircuitBreakerConfig()
        mixin._configure_circuit_breaker("test_service", config)

        # Verify it exists
        assert "test_service" in mixin._circuit_breakers
        assert "test_service" in mixin._circuit_breaker_configs

        # Remove it
        mixin._remove_circuit_breaker("test_service")

        # Verify it's gone
        assert "test_service" not in mixin._circuit_breakers
        assert "test_service" not in mixin._circuit_breaker_configs

    def test_get_all_circuit_breaker_states(self):
        """Test getting all circuit breaker states."""
        mixin = TestableCircuitBreakerMixin()

        # Setup multiple circuit breakers
        configs = {
            "service_a": ModelCircuitBreakerConfig(),
            "service_b": ModelCircuitBreakerConfig(),
        }
        mixin._setup_circuit_breakers(configs)

        states = mixin._get_all_circuit_breaker_states()

        assert len(states) == 2
        assert "service_a" in states
        assert "service_b" in states
        assert all("state" in state for state in states.values())

    def test_health_check_with_circuit_breaker_healthy(self):
        """Test health check with healthy circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        # Mock healthy circuit breaker
        mock_breaker = Mock()
        mock_breaker.get_state.return_value = CircuitBreakerState.CLOSED
        mixin._circuit_breakers["test_service"] = mock_breaker

        # Mock metrics
        with patch.object(mixin, "_get_circuit_breaker_metrics") as mock_metrics:
            mock_metrics.return_value = {"failure_count": 0}

            health = mixin._health_check_with_circuit_breaker("test_service")

            assert health["service_name"] == "test_service"
            assert health["health_status"] == "healthy"
            assert health["circuit_breaker"]["state"] == "closed"

    def test_health_check_with_circuit_breaker_recovering(self):
        """Test health check with recovering circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        # Mock recovering circuit breaker
        mock_breaker = Mock()
        mock_breaker.get_state.return_value = CircuitBreakerState.HALF_OPEN
        mixin._circuit_breakers["test_service"] = mock_breaker

        # Mock metrics
        with patch.object(mixin, "_get_circuit_breaker_metrics") as mock_metrics:
            mock_metrics.return_value = {"failure_count": 2}

            health = mixin._health_check_with_circuit_breaker("test_service")

            assert health["health_status"] == "recovering"
            assert health["circuit_breaker"]["state"] == "half_open"

    def test_health_check_with_circuit_breaker_unhealthy(self):
        """Test health check with open circuit breaker."""
        mixin = TestableCircuitBreakerMixin()

        # Mock open circuit breaker
        mock_breaker = Mock()
        mock_breaker.get_state.return_value = CircuitBreakerState.OPEN
        mixin._circuit_breakers["test_service"] = mock_breaker

        # Mock metrics
        with patch.object(mixin, "_get_circuit_breaker_metrics") as mock_metrics:
            mock_metrics.return_value = {"failure_count": 5}

            health = mixin._health_check_with_circuit_breaker("test_service")

            assert health["health_status"] == "unhealthy"
            assert health["circuit_breaker"]["state"] == "open"

    def test_thread_safety(self):
        """Test thread safety of circuit breaker operations."""
        mixin = TestableCircuitBreakerMixin()
        results = []
        errors = []

        def concurrent_access(service_name):
            try:
                # Simulate concurrent access to circuit breakers
                for i in range(10):
                    breaker = mixin._get_circuit_breaker(f"{service_name}_{i}")
                    state = mixin._get_circuit_breaker_state(f"{service_name}_{i}")
                    results.append((service_name, i, breaker is not None, state))
                    time.sleep(
                        0.001
                    )  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)

        # Run multiple threads concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_access, args=(f"service_{i}",))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Verify expected number of results
        assert len(results) == 50  # 5 threads * 10 operations each

        # Verify all operations succeeded
        assert all(result[2] for result in results)  # All breakers created


class TestCircuitBreakerConfigFactories:
    """Test suite for circuit breaker configuration factory functions."""

    def test_create_default_circuit_breaker_config(self):
        """Test creating default circuit breaker configuration."""
        config = create_default_circuit_breaker_config()

        assert isinstance(config, ModelCircuitBreakerConfig)
        assert config.failure_threshold == 5
        assert config.recovery_timeout_seconds == 30
        assert config.request_timeout_seconds == 10.0

    def test_create_default_circuit_breaker_config_custom_values(self):
        """Test creating default configuration with custom values."""
        config = create_default_circuit_breaker_config(
            failure_threshold=3,
            recovery_timeout_seconds=60,
            request_timeout_seconds=5.0,
        )

        assert config.failure_threshold == 3
        assert config.recovery_timeout_seconds == 60
        assert config.request_timeout_seconds == 5.0

    def test_create_strict_circuit_breaker_config(self):
        """Test creating strict circuit breaker configuration."""
        config = create_strict_circuit_breaker_config()

        assert isinstance(config, ModelCircuitBreakerConfig)
        assert config.failure_threshold == 2
        assert config.recovery_timeout_seconds == 60
        assert config.request_timeout_seconds == 5.0
        assert config.failure_rate_threshold == 0.3

    def test_create_lenient_circuit_breaker_config(self):
        """Test creating lenient circuit breaker configuration."""
        config = create_lenient_circuit_breaker_config()

        assert isinstance(config, ModelCircuitBreakerConfig)
        assert config.failure_threshold == 10
        assert config.recovery_timeout_seconds == 15
        assert config.request_timeout_seconds == 30.0
        assert config.failure_rate_threshold == 0.8

    def test_factory_configs_have_different_settings(self):
        """Test that factory configs produce different settings."""
        default_config = create_default_circuit_breaker_config()
        strict_config = create_strict_circuit_breaker_config()
        lenient_config = create_lenient_circuit_breaker_config()

        # Strict should have lower thresholds than default
        assert strict_config.failure_threshold < default_config.failure_threshold
        assert (
            strict_config.request_timeout_seconds
            < default_config.request_timeout_seconds
        )

        # Lenient should have higher thresholds than default
        assert lenient_config.failure_threshold > default_config.failure_threshold
        assert (
            lenient_config.request_timeout_seconds
            > default_config.request_timeout_seconds
        )
        assert (
            lenient_config.recovery_timeout_seconds
            < default_config.recovery_timeout_seconds
        )
