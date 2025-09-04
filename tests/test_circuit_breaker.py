#!/usr/bin/env python3
"""
Tests for circuit breaker pattern implementation.

Comprehensive tests for ExternalDependencyCircuitBreaker, state transitions,
metrics collection, configuration, and integration patterns.
"""

import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from omnibase_core.core.resilience import (
    CircuitBreakerEvent,
    CircuitBreakerException,
    CircuitBreakerFactory,
    CircuitBreakerMetrics,
    CircuitBreakerOpenException,
    CircuitBreakerState,
    CircuitBreakerTimeoutException,
    ExternalDependencyCircuitBreaker,
    ModelCircuitBreakerConfig,
    get_circuit_breaker,
    list_circuit_breakers,
    register_circuit_breaker,
)


class TestModelCircuitBreakerConfig:
    """Test ModelCircuitBreakerConfig configuration model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ModelCircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.failure_rate_threshold == 0.5
        assert config.minimum_request_threshold == 10
        assert config.recovery_timeout_seconds == 60
        assert config.success_threshold == 3
        assert config.request_timeout_seconds == 10.0
        assert config.enable_metrics is True
        assert config.log_state_changes is True

    def test_validation(self):
        """Test configuration validation."""
        # Valid configuration
        config = ModelCircuitBreakerConfig(
            failure_threshold=3, failure_rate_threshold=0.3, recovery_timeout_seconds=30
        )
        assert config.failure_threshold == 3

        # Invalid failure rate
        with pytest.raises(ValueError):
            ModelCircuitBreakerConfig(failure_rate_threshold=1.5)

        with pytest.raises(ValueError):
            ModelCircuitBreakerConfig(failure_rate_threshold=-0.1)

    def test_from_environment(self):
        """Test loading configuration from environment."""
        os.environ["CB_TEST_FAILURE_THRESHOLD"] = "3"
        os.environ["CB_TEST_FAILURE_RATE_THRESHOLD"] = "0.3"
        os.environ["CB_TEST_RECOVERY_TIMEOUT_SECONDS"] = "45"

        try:
            config = ModelCircuitBreakerConfig.from_environment(prefix="CB_TEST")

            assert config.failure_threshold == 3
            assert config.failure_rate_threshold == 0.3
            assert config.recovery_timeout_seconds == 45
        finally:
            # Clean up
            for key in [
                "CB_TEST_FAILURE_THRESHOLD",
                "CB_TEST_FAILURE_RATE_THRESHOLD",
                "CB_TEST_RECOVERY_TIMEOUT_SECONDS",
            ]:
                os.environ.pop(key, None)


class TestCircuitBreakerMetrics:
    """Test CircuitBreakerMetrics functionality."""

    def test_initial_state(self):
        """Test initial metrics state."""
        metrics = CircuitBreakerMetrics()

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.current_state == CircuitBreakerState.CLOSED
        assert metrics.get_failure_rate() == 0.0
        assert metrics.get_success_rate() == 1.0

    def test_failure_rate_calculation(self):
        """Test failure rate calculation."""
        metrics = CircuitBreakerMetrics()

        # No requests
        assert metrics.get_failure_rate() == 0.0

        # Some requests
        metrics.requests_in_window = 10
        metrics.failures_in_window = 3
        assert metrics.get_failure_rate() == 0.3

        # All failures
        metrics.failures_in_window = 10
        assert metrics.get_failure_rate() == 1.0

    def test_reset_window(self):
        """Test window reset functionality."""
        metrics = CircuitBreakerMetrics()

        # Set some window data
        metrics.requests_in_window = 10
        metrics.failures_in_window = 3
        metrics.successes_in_window = 7

        # Reset window
        metrics.reset_window()

        assert metrics.requests_in_window == 0
        assert metrics.failures_in_window == 0
        assert metrics.successes_in_window == 0


class TestExternalDependencyCircuitBreaker:
    """Test ExternalDependencyCircuitBreaker functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.config = ModelCircuitBreakerConfig(
            failure_threshold=3,
            failure_rate_threshold=0.5,
            minimum_request_threshold=5,
            recovery_timeout_seconds=1,  # Short for testing
            success_threshold=2,
            request_timeout_seconds=1.0,
        )
        self.circuit_breaker = ExternalDependencyCircuitBreaker(
            "test-service", self.config
        )

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful function call."""

        async def success_func():
            return "success"

        result = await self.circuit_breaker.call(success_func)

        assert result == "success"
        assert self.circuit_breaker.get_state() == CircuitBreakerState.CLOSED

        metrics = self.circuit_breaker.get_metrics()
        assert metrics.successful_requests == 1
        assert metrics.total_requests == 1
        assert metrics.failed_requests == 0

    @pytest.mark.asyncio
    async def test_failed_call(self):
        """Test failed function call."""

        async def failing_func():
            raise Exception("Service unavailable")

        with pytest.raises(Exception, match="Service unavailable"):
            await self.circuit_breaker.call(failing_func)

        metrics = self.circuit_breaker.get_metrics()
        assert metrics.failed_requests == 1
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0

    @pytest.mark.asyncio
    async def test_timeout_call(self):
        """Test function call timeout."""

        async def slow_func():
            await asyncio.sleep(2.0)  # Longer than timeout
            return "slow"

        with pytest.raises(CircuitBreakerTimeoutException):
            await self.circuit_breaker.call(slow_func)

        metrics = self.circuit_breaker.get_metrics()
        assert metrics.timeout_requests == 1

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Test circuit opens after failure threshold."""

        async def failing_func():
            raise Exception("Service down")

        # Make requests up to minimum threshold
        for i in range(self.config.minimum_request_threshold):
            try:
                await self.circuit_breaker.call(failing_func)
            except Exception:
                pass

        # Circuit should now be open
        assert self.circuit_breaker.get_state() == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_blocks_when_open(self):
        """Test circuit blocks requests when open."""
        # Force circuit open
        await self.circuit_breaker.force_open()

        async def any_func():
            return "should not execute"

        with pytest.raises(CircuitBreakerOpenException):
            await self.circuit_breaker.call(any_func)

    @pytest.mark.asyncio
    async def test_fallback_execution(self):
        """Test fallback function execution when circuit is open."""
        await self.circuit_breaker.force_open()

        async def blocked_func():
            return "blocked"

        async def fallback_func():
            return "fallback"

        result = await self.circuit_breaker.call(blocked_func, fallback=fallback_func)
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_half_open_transition(self):
        """Test transition to half-open state."""
        # Force open circuit
        await self.circuit_breaker.force_open()
        assert self.circuit_breaker.get_state() == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)  # Slightly longer than recovery timeout

        # Next call should transition to half-open
        async def test_func():
            return "testing"

        result = await self.circuit_breaker.call(test_func)
        assert result == "testing"
        assert self.circuit_breaker.get_state() == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_recovery(self):
        """Test recovery from half-open to closed."""
        await self.circuit_breaker._transition_to_half_open()

        async def success_func():
            return "success"

        # Make successful calls to reach success threshold
        for i in range(self.config.success_threshold):
            result = await self.circuit_breaker.call(success_func)
            assert result == "success"

        # Circuit should be closed now
        assert self.circuit_breaker.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """Test transition back to open on failure in half-open."""
        await self.circuit_breaker._transition_to_half_open()

        async def failing_func():
            raise Exception("Still failing")

        with pytest.raises(Exception):
            await self.circuit_breaker.call(failing_func)

        # Circuit should be open again
        assert self.circuit_breaker.get_state() == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_context_manager_success(self):
        """Test context manager with successful operation."""
        async with self.circuit_breaker.protect() as cb:
            # Simulate successful operation
            await asyncio.sleep(0.1)
            cb.set_result("success")

        metrics = self.circuit_breaker.get_metrics()
        assert metrics.successful_requests == 1

    @pytest.mark.asyncio
    async def test_context_manager_failure(self):
        """Test context manager with failure."""
        with pytest.raises(ValueError):
            async with self.circuit_breaker.protect():
                raise ValueError("Operation failed")

        metrics = self.circuit_breaker.get_metrics()
        assert metrics.failed_requests == 1

    @pytest.mark.asyncio
    async def test_context_manager_timeout(self):
        """Test context manager with timeout."""
        with pytest.raises(CircuitBreakerTimeoutException):
            async with self.circuit_breaker.protect(timeout=0.1):
                await asyncio.sleep(0.2)  # Longer than timeout

    @pytest.mark.asyncio
    async def test_context_manager_circuit_open(self):
        """Test context manager when circuit is open."""
        await self.circuit_breaker.force_open()

        with pytest.raises(CircuitBreakerOpenException):
            async with self.circuit_breaker.protect():
                pass

    @pytest.mark.asyncio
    async def test_context_manager_with_fallback(self):
        """Test context manager with fallback result."""
        await self.circuit_breaker.force_open()

        async with self.circuit_breaker.protect(fallback_result="fallback") as cb:
            pass

        # Should not raise exception due to fallback
        assert cb.result == "fallback"
        assert cb.is_fallback is True

    def test_manual_state_control(self):
        """Test manual state control methods."""
        # Initial state
        assert self.circuit_breaker.get_state() == CircuitBreakerState.CLOSED

        # Force open
        asyncio.run(self.circuit_breaker.force_open())
        assert self.circuit_breaker.get_state() == CircuitBreakerState.OPEN

        # Force close
        asyncio.run(self.circuit_breaker.force_close())
        assert self.circuit_breaker.get_state() == CircuitBreakerState.CLOSED

        # Reset
        asyncio.run(self.circuit_breaker.reset())
        metrics = self.circuit_breaker.get_metrics()
        assert metrics.total_requests == 0

    @pytest.mark.asyncio
    async def test_event_listeners(self):
        """Test event listener functionality."""
        events_received = []

        async def event_handler(cb, event, metrics):
            events_received.append((event, metrics.current_state))

        # Add event listeners
        self.circuit_breaker.add_event_listener(
            CircuitBreakerEvent.SUCCESS, event_handler
        )
        self.circuit_breaker.add_event_listener(
            CircuitBreakerEvent.FAILURE, event_handler
        )
        self.circuit_breaker.add_event_listener(
            CircuitBreakerEvent.STATE_CHANGE, event_handler
        )

        # Generate events
        async def success_func():
            return "success"

        async def failing_func():
            raise Exception("fail")

        # Success event
        await self.circuit_breaker.call(success_func)

        # Failure event
        try:
            await self.circuit_breaker.call(failing_func)
        except Exception:
            pass

        # State change event
        await self.circuit_breaker.force_open()

        # Check events were received
        assert len(events_received) >= 3
        event_types = [event[0] for event in events_received]
        assert CircuitBreakerEvent.SUCCESS in event_types
        assert CircuitBreakerEvent.FAILURE in event_types
        assert CircuitBreakerEvent.STATE_CHANGE in event_types


class TestCircuitBreakerFactory:
    """Test CircuitBreakerFactory functionality."""

    def test_create_fast_fail(self):
        """Test creating fast-fail circuit breaker."""
        cb = CircuitBreakerFactory.create_fast_fail("test-service")

        assert cb.service_name == "test-service"
        assert cb.config.failure_threshold == 3
        assert cb.config.recovery_timeout_seconds == 30

    def test_create_resilient(self):
        """Test creating resilient circuit breaker."""
        cb = CircuitBreakerFactory.create_resilient("test-service")

        assert cb.service_name == "test-service"
        assert cb.config.failure_threshold == 10
        assert cb.config.recovery_timeout_seconds == 120
        assert cb.config.exponential_backoff is True

    def test_create_from_environment(self):
        """Test creating circuit breaker from environment."""
        os.environ["CB_TEST_SERVICE_FAILURE_THRESHOLD"] = "5"
        os.environ["CB_TEST_SERVICE_RECOVERY_TIMEOUT_SECONDS"] = "90"

        try:
            cb = CircuitBreakerFactory.create_from_environment(
                "test-service", prefix="CB_TEST_SERVICE"
            )

            assert cb.config.failure_threshold == 5
            assert cb.config.recovery_timeout_seconds == 90
        finally:
            # Clean up
            for key in [
                "CB_TEST_SERVICE_FAILURE_THRESHOLD",
                "CB_TEST_SERVICE_RECOVERY_TIMEOUT_SECONDS",
            ]:
                os.environ.pop(key, None)


class TestCircuitBreakerRegistry:
    """Test global circuit breaker registry functionality."""

    def setup_method(self):
        """Clear registry for testing."""
        # Clear global registry
        import omnibase_core.core.resilience.circuit_breaker as cb_module

        cb_module._circuit_breaker_registry.clear()

    def test_get_circuit_breaker_create(self):
        """Test get_circuit_breaker with create_if_missing=True."""
        cb = get_circuit_breaker("new-service", create_if_missing=True)

        assert cb is not None
        assert cb.service_name == "new-service"

    def test_get_circuit_breaker_no_create(self):
        """Test get_circuit_breaker with create_if_missing=False."""
        cb = get_circuit_breaker("nonexistent-service", create_if_missing=False)

        assert cb is None

    def test_register_circuit_breaker(self):
        """Test registering circuit breaker in global registry."""
        cb = ExternalDependencyCircuitBreaker("registered-service")
        register_circuit_breaker("registered-service", cb)

        retrieved = get_circuit_breaker("registered-service", create_if_missing=False)
        assert retrieved is cb

    def test_list_circuit_breakers(self):
        """Test listing all circuit breakers."""
        cb1 = ExternalDependencyCircuitBreaker("service-1")
        cb2 = ExternalDependencyCircuitBreaker("service-2")

        register_circuit_breaker("service-1", cb1)
        register_circuit_breaker("service-2", cb2)

        # Add some metrics
        cb1.metrics.total_requests = 10
        cb1.metrics.failed_requests = 2
        cb1.metrics.requests_in_window = 10
        cb1.metrics.failures_in_window = 2

        circuit_breakers = list_circuit_breakers()

        assert len(circuit_breakers) == 2
        assert "service-1" in circuit_breakers
        assert "service-2" in circuit_breakers

        service1_info = circuit_breakers["service-1"]
        assert service1_info["state"] == "closed"
        assert service1_info["total_requests"] == 10
        assert service1_info["failure_rate"] == 0.2


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker system."""

    @pytest.mark.asyncio
    async def test_full_failure_recovery_cycle(self):
        """Test complete failure and recovery cycle."""
        config = ModelCircuitBreakerConfig(
            failure_threshold=3,
            minimum_request_threshold=5,
            recovery_timeout_seconds=0.5,  # Short for testing
            success_threshold=2,
        )

        cb = ExternalDependencyCircuitBreaker("integration-test", config)

        # Simulate failing service that recovers
        call_count = 0

        async def service_call():
            nonlocal call_count
            call_count += 1

            # Fail for first 8 calls, then succeed
            if call_count <= 8:
                raise Exception("Service down")
            return f"success-{call_count}"

        # Phase 1: Generate failures to open circuit
        for i in range(6):  # More than minimum_request_threshold
            try:
                await cb.call(service_call)
            except Exception:
                pass

        # Circuit should be open
        assert cb.get_state() == CircuitBreakerState.OPEN

        # Phase 2: Wait for recovery timeout
        await asyncio.sleep(0.6)

        # Phase 3: Recovery attempts should succeed
        for i in range(3):
            result = await cb.call(service_call)
            assert result.startswith("success")

        # Circuit should be closed
        assert cb.get_state() == CircuitBreakerState.CLOSED

        # Verify final metrics
        metrics = cb.get_metrics()
        assert metrics.state_changes >= 2  # Open -> Half-open -> Closed

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff behavior."""
        config = ModelCircuitBreakerConfig(
            failure_threshold=2,
            minimum_request_threshold=3,
            recovery_timeout_seconds=1,
            exponential_backoff=True,
            max_backoff_seconds=10,
        )

        cb = ExternalDependencyCircuitBreaker("backoff-test", config)

        async def failing_service():
            raise Exception("Persistent failure")

        # Force multiple failures to trigger backoff
        for i in range(5):
            try:
                await cb.call(failing_service)
            except Exception:
                pass

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Check that backoff time increases
        initial_backoff = cb._current_backoff

        # Trigger another failure cycle
        await asyncio.sleep(initial_backoff + 0.1)  # Wait past initial backoff

        try:
            await cb.call(
                failing_service
            )  # This should transition to half-open then back to open
        except Exception:
            pass

        # Backoff should have increased
        assert cb._current_backoff > initial_backoff

    @pytest.mark.asyncio
    async def test_multiple_services_isolation(self):
        """Test that circuit breakers for different services are isolated."""
        service_a_cb = ExternalDependencyCircuitBreaker("service-a")
        service_b_cb = ExternalDependencyCircuitBreaker("service-b")

        async def failing_service_a():
            raise Exception("Service A down")

        async def working_service_b():
            return "Service B works"

        # Fail service A multiple times
        for i in range(10):
            try:
                await service_a_cb.call(failing_service_a)
            except Exception:
                pass

        # Service B should still work
        result = await service_b_cb.call(working_service_b)
        assert result == "Service B works"

        # States should be different
        assert service_a_cb.get_state() == CircuitBreakerState.OPEN
        assert service_b_cb.get_state() == CircuitBreakerState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
