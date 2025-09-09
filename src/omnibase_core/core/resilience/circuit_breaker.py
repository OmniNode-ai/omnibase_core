#!/usr/bin/env python3
"""
Advanced circuit breaker implementation for external dependencies.

Provides fault tolerance, cascading failure prevention, and graceful degradation
for external service calls with comprehensive monitoring and configuration.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TypeVar

from pydantic import Field, field_validator

from omnibase_core.core.configuration.environment_config import ModelEnvironmentConfig

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CircuitBreakerState(str, Enum):
    """Circuit breaker states with clear semantics."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Service is failing, requests fail fast
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


class CircuitBreakerEvent(str, Enum):
    """Events that can occur in circuit breaker lifecycle."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    STATE_CHANGE = "state_change"
    FALLBACK_EXECUTED = "fallback_executed"


@dataclass
class CircuitBreakerMetrics:
    """Real-time circuit breaker metrics."""

    # Request counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0

    # State tracking
    current_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    state_changes: int = 0
    last_state_change: datetime | None = None

    # Timing metrics
    last_success_time: datetime | None = None
    last_failure_time: datetime | None = None
    average_response_time_ms: float = 0.0

    # Window-based metrics (rolling)
    requests_in_window: int = 0
    failures_in_window: int = 0
    successes_in_window: int = 0

    # Half-open state tracking
    half_open_requests: int = 0
    half_open_successes: int = 0
    half_open_failures: int = 0

    def get_failure_rate(self) -> float:
        """Calculate current failure rate."""
        if self.requests_in_window == 0:
            return 0.0
        return self.failures_in_window / self.requests_in_window

    def get_success_rate(self) -> float:
        """Calculate current success rate."""
        return 1.0 - self.get_failure_rate()

    def reset_window(self) -> None:
        """Reset window-based metrics."""
        self.requests_in_window = 0
        self.failures_in_window = 0
        self.successes_in_window = 0


class ModelCircuitBreakerConfig(ModelEnvironmentConfig):
    """Environment-configurable circuit breaker settings."""

    # Core thresholds
    failure_threshold: int = Field(
        default=5,
        description="Number of failures before opening circuit",
        ge=1,
        le=100,
    )

    failure_rate_threshold: float = Field(
        default=0.5,
        description="Failure rate (0.0-1.0) to open circuit",
        ge=0.0,
        le=1.0,
    )

    minimum_request_threshold: int = Field(
        default=10,
        description="Minimum requests before evaluating failure rate",
        ge=1,
        le=1000,
    )

    # Recovery settings
    recovery_timeout_seconds: int = Field(
        default=60,
        description="Time to wait before attempting recovery",
        ge=10,
        le=3600,
    )

    success_threshold: int = Field(
        default=3,
        description="Successes needed to close from half-open",
        ge=1,
        le=20,
    )

    half_open_max_requests: int = Field(
        default=5,
        description="Maximum requests in half-open state",
        ge=1,
        le=50,
    )

    # Timing settings
    request_timeout_seconds: float = Field(
        default=10.0,
        description="Request timeout in seconds",
        ge=0.1,
        le=300.0,
    )

    window_size_seconds: int = Field(
        default=60,
        description="Rolling window size for metrics",
        ge=30,
        le=3600,
    )

    # Advanced settings
    slow_call_threshold_ms: int | None = Field(
        default=None,
        description="Threshold for considering calls slow",
        ge=100,
        le=60000,
    )

    slow_call_rate_threshold: float | None = Field(
        default=None,
        description="Slow call rate to trigger opening",
        ge=0.0,
        le=1.0,
    )

    exponential_backoff: bool = Field(
        default=True,
        description="Use exponential backoff for recovery timeout",
    )

    max_backoff_seconds: int = Field(
        default=300,
        description="Maximum backoff time in seconds",
        ge=60,
        le=3600,
    )

    # Monitoring and logging
    enable_metrics: bool = Field(
        default=True,
        description="Enable detailed metrics collection",
    )

    log_state_changes: bool = Field(
        default=True,
        description="Log circuit breaker state changes",
    )

    @field_validator("failure_rate_threshold")
    @classmethod
    def validate_failure_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("failure_rate_threshold must be between 0.0 and 1.0")
        return v


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker prevents request execution."""

    def __init__(
        self,
        service_name: str,
        state: CircuitBreakerState,
        metrics: CircuitBreakerMetrics | None = None,
    ):
        self.service_name = service_name
        self.state = state
        self.metrics = metrics
        super().__init__(
            f"Circuit breaker is {state.value} for service '{service_name}'",
        )


class CircuitBreakerOpenException(CircuitBreakerException):
    """Exception for when circuit breaker is in OPEN state."""


class CircuitBreakerTimeoutException(CircuitBreakerException):
    """Exception for when request times out."""


class ExternalDependencyCircuitBreaker:
    """
    Advanced circuit breaker for external dependencies.

    Features:
    - Configurable failure detection
    - Automatic state management
    - Comprehensive metrics
    - Fallback support
    - Environment-based configuration
    - Async/await support
    """

    def __init__(
        self,
        service_name: str,
        config: ModelCircuitBreakerConfig | None = None,
    ):
        self.service_name = service_name
        self.config = config or ModelCircuitBreakerConfig.from_environment(
            prefix=f"CIRCUIT_BREAKER_{service_name.upper()}",
        )

        # State management
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
        self._window_start = datetime.utcnow()

        # Backoff tracking
        self._failure_count_for_backoff = 0
        self._current_backoff = self.config.recovery_timeout_seconds

        # Event callbacks
        self._event_callbacks: dict[CircuitBreakerEvent, list] = {
            event: [] for event in CircuitBreakerEvent
        }

        logger.info(f"Initialized circuit breaker for service: {service_name}")

    async def call(
        self,
        func: Callable[[], Awaitable[T]],
        fallback: Callable[[], Awaitable[T]] | None = None,
        timeout: float | None = None,
    ) -> T:
        """
        Execute function through circuit breaker with optional fallback.

        Args:
            func: Async function to execute
            fallback: Optional fallback function
            timeout: Override default timeout

        Returns:
            Result of function execution

        Raises:
            CircuitBreakerOpenException: If circuit is open and no fallback
            CircuitBreakerTimeoutException: If request times out
            Any exception raised by func or fallback
        """
        async with self._lock:
            # Check if request should be allowed
            if not await self._should_allow_request():
                if fallback:
                    logger.info(
                        f"Circuit breaker open for {self.service_name}, executing fallback",
                    )
                    await self._emit_event(CircuitBreakerEvent.FALLBACK_EXECUTED)
                    return await self._execute_with_timeout(fallback, timeout)
                raise CircuitBreakerOpenException(
                    self.service_name,
                    self.metrics.current_state,
                    self.metrics,
                )

            # Execute the function
            start_time = time.time()
            try:
                result = await self._execute_with_timeout(func, timeout)

                # Record success
                execution_time = (time.time() - start_time) * 1000  # ms
                await self._record_success(execution_time)

                return result

            except TimeoutError:
                await self._record_timeout()
                raise CircuitBreakerTimeoutException(
                    self.service_name,
                    self.metrics.current_state,
                    self.metrics,
                )
            except Exception as e:
                await self._record_failure(e)
                raise

    @asynccontextmanager
    async def protect(
        self,
        timeout: float | None = None,
        fallback_result: T | None = None,
    ):
        """
        Context manager for circuit breaker protection.

        Usage:
            async with circuit_breaker.protect() as cb:
                result = await some_external_call()
                cb.set_result(result)
        """
        if not await self._should_allow_request():
            if fallback_result is not None:
                yield _CircuitBreakerContext(fallback_result, is_fallback=True)
                return
            else:
                raise CircuitBreakerOpenException(
                    self.service_name,
                    self.metrics.current_state,
                    self.metrics,
                )

        context = _CircuitBreakerContext()
        start_time = time.time()

        try:
            # Set timeout if specified
            if timeout or self.config.request_timeout_seconds:
                timeout_val = timeout or self.config.request_timeout_seconds
                await asyncio.wait_for(
                    self._yield_context(context),
                    timeout=timeout_val,
                )
            else:
                yield context

            # Record success if context completed successfully
            if not context.has_exception:
                execution_time = (time.time() - start_time) * 1000
                await self._record_success(execution_time)

        except TimeoutError:
            context.has_exception = True
            await self._record_timeout()
            raise CircuitBreakerTimeoutException(
                self.service_name,
                self.metrics.current_state,
                self.metrics,
            )
        except Exception as e:
            context.has_exception = True
            await self._record_failure(e)
            raise

    async def _yield_context(self, context):
        """Helper to yield context in async context manager."""
        yield context

    async def _execute_with_timeout(
        self,
        func: Callable[[], Awaitable[T]],
        timeout: float | None,
    ) -> T:
        """Execute function with timeout."""
        timeout_val = timeout or self.config.request_timeout_seconds
        return await asyncio.wait_for(func(), timeout=timeout_val)

    async def _should_allow_request(self) -> bool:
        """Determine if request should be allowed through."""
        await self._update_window()

        current_state = self.metrics.current_state

        if current_state == CircuitBreakerState.CLOSED:
            return True

        if current_state == CircuitBreakerState.OPEN:
            # Check if we should transition to half-open
            if await self._should_transition_to_half_open():
                await self._transition_to_half_open()
                return True
            return False

        if current_state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests in half-open
            return self.metrics.half_open_requests < self.config.half_open_max_requests

        return False

    async def _record_success(self, execution_time_ms: float) -> None:
        """Record successful request."""
        self.metrics.successful_requests += 1
        self.metrics.total_requests += 1
        self.metrics.requests_in_window += 1
        self.metrics.successes_in_window += 1
        self.metrics.last_success_time = datetime.utcnow()

        # Update average response time
        self._update_average_response_time(execution_time_ms)

        # Handle half-open state
        if self.metrics.current_state == CircuitBreakerState.HALF_OPEN:
            self.metrics.half_open_successes += 1
            self.metrics.half_open_requests += 1

            if self.metrics.half_open_successes >= self.config.success_threshold:
                await self._transition_to_closed()

        await self._emit_event(CircuitBreakerEvent.SUCCESS)

    async def _record_failure(self, exception: Exception) -> None:
        """Record failed request."""
        self.metrics.failed_requests += 1
        self.metrics.total_requests += 1
        self.metrics.requests_in_window += 1
        self.metrics.failures_in_window += 1
        self.metrics.last_failure_time = datetime.utcnow()

        # Handle state transitions
        if self.metrics.current_state == CircuitBreakerState.HALF_OPEN:
            self.metrics.half_open_failures += 1
            self.metrics.half_open_requests += 1
            await self._transition_to_open()

        elif self.metrics.current_state == CircuitBreakerState.CLOSED:
            if await self._should_open_circuit():
                await self._transition_to_open()

        await self._emit_event(CircuitBreakerEvent.FAILURE)

    async def _record_timeout(self) -> None:
        """Record timed out request."""
        self.metrics.timeout_requests += 1
        await self._record_failure(TimeoutError())
        await self._emit_event(CircuitBreakerEvent.TIMEOUT)

    def _update_average_response_time(self, execution_time_ms: float) -> None:
        """Update rolling average response time."""
        if self.metrics.successful_requests == 1:
            self.metrics.average_response_time_ms = execution_time_ms
        else:
            # Simple exponential moving average
            alpha = 0.1
            self.metrics.average_response_time_ms = (
                alpha * execution_time_ms
                + (1 - alpha) * self.metrics.average_response_time_ms
            )

    async def _should_open_circuit(self) -> bool:
        """Check if circuit should be opened."""
        # Need minimum requests
        if self.metrics.requests_in_window < self.config.minimum_request_threshold:
            return False

        # Check absolute failure threshold
        if self.metrics.failures_in_window >= self.config.failure_threshold:
            return True

        # Check failure rate threshold
        failure_rate = self.metrics.get_failure_rate()
        return failure_rate >= self.config.failure_rate_threshold

    async def _should_transition_to_half_open(self) -> bool:
        """Check if should transition from open to half-open."""
        if not self.metrics.last_state_change:
            return True

        time_since_open = datetime.utcnow() - self.metrics.last_state_change
        return time_since_open.total_seconds() >= self._current_backoff

    async def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        old_state = self.metrics.current_state
        self.metrics.current_state = CircuitBreakerState.OPEN
        self.metrics.last_state_change = datetime.utcnow()
        self.metrics.state_changes += 1

        # Reset half-open counters
        self.metrics.half_open_requests = 0
        self.metrics.half_open_successes = 0
        self.metrics.half_open_failures = 0

        # Update backoff
        self._failure_count_for_backoff += 1
        if self.config.exponential_backoff:
            self._current_backoff = min(
                self.config.recovery_timeout_seconds
                * (2 ** (self._failure_count_for_backoff - 1)),
                self.config.max_backoff_seconds,
            )

        if self.config.log_state_changes:
            logger.warning(
                f"Circuit breaker for {self.service_name} transitioned: "
                f"{old_state} -> {self.metrics.current_state} "
                f"(backoff: {self._current_backoff}s)",
            )

        await self._emit_event(CircuitBreakerEvent.STATE_CHANGE)

    async def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        old_state = self.metrics.current_state
        self.metrics.current_state = CircuitBreakerState.HALF_OPEN
        self.metrics.last_state_change = datetime.utcnow()
        self.metrics.state_changes += 1

        # Reset half-open counters
        self.metrics.half_open_requests = 0
        self.metrics.half_open_successes = 0
        self.metrics.half_open_failures = 0

        if self.config.log_state_changes:
            logger.info(
                f"Circuit breaker for {self.service_name} transitioned: "
                f"{old_state} -> {self.metrics.current_state}",
            )

        await self._emit_event(CircuitBreakerEvent.STATE_CHANGE)

    async def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        old_state = self.metrics.current_state
        self.metrics.current_state = CircuitBreakerState.CLOSED
        self.metrics.last_state_change = datetime.utcnow()
        self.metrics.state_changes += 1

        # Reset counters and backoff
        self.metrics.reset_window()
        self._failure_count_for_backoff = 0
        self._current_backoff = self.config.recovery_timeout_seconds

        # Reset half-open counters
        self.metrics.half_open_requests = 0
        self.metrics.half_open_successes = 0
        self.metrics.half_open_failures = 0

        if self.config.log_state_changes:
            logger.info(
                f"Circuit breaker for {self.service_name} transitioned: "
                f"{old_state} -> {self.metrics.current_state} (recovered)",
            )

        await self._emit_event(CircuitBreakerEvent.STATE_CHANGE)

    async def _update_window(self) -> None:
        """Update rolling window metrics."""
        now = datetime.utcnow()
        window_duration = timedelta(seconds=self.config.window_size_seconds)

        if now - self._window_start > window_duration:
            # Reset window
            self._window_start = now
            self.metrics.reset_window()

    async def _emit_event(self, event: CircuitBreakerEvent) -> None:
        """Emit event to registered callbacks."""
        callbacks = self._event_callbacks.get(event, [])
        for callback in callbacks:
            try:
                await callback(self, event, self.metrics)
            except Exception as e:
                logger.error(f"Error in circuit breaker event callback: {e}")

    # Public API methods

    def add_event_listener(
        self,
        event: CircuitBreakerEvent,
        callback: Callable[
            [
                "ExternalDependencyCircuitBreaker",
                CircuitBreakerEvent,
                CircuitBreakerMetrics,
            ],
            Awaitable[None],
        ],
    ) -> None:
        """Add event listener for circuit breaker events."""
        self._event_callbacks[event].append(callback)

    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics snapshot."""
        return self.metrics

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.metrics.current_state

    async def force_open(self) -> None:
        """Force circuit breaker to OPEN state."""
        await self._transition_to_open()

    async def force_close(self) -> None:
        """Force circuit breaker to CLOSED state."""
        await self._transition_to_closed()

    async def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.metrics = CircuitBreakerMetrics()
        self._window_start = datetime.utcnow()
        self._failure_count_for_backoff = 0
        self._current_backoff = self.config.recovery_timeout_seconds

        logger.info(f"Reset circuit breaker for service: {self.service_name}")


@dataclass
class _CircuitBreakerContext:
    """Internal context for circuit breaker protection."""

    result: Any | None = None
    is_fallback: bool = False
    has_exception: bool = False

    def set_result(self, result: Any) -> None:
        """Set the result of the operation."""
        self.result = result


# Factory for creating circuit breakers with common configurations
class CircuitBreakerFactory:
    """Factory for creating pre-configured circuit breakers."""

    @staticmethod
    def create_fast_fail(service_name: str) -> ExternalDependencyCircuitBreaker:
        """Create circuit breaker optimized for fast failure detection."""
        config = ModelCircuitBreakerConfig(
            failure_threshold=3,
            failure_rate_threshold=0.3,
            minimum_request_threshold=5,
            recovery_timeout_seconds=30,
            success_threshold=2,
            half_open_max_requests=3,
            request_timeout_seconds=5.0,
            window_size_seconds=60,
        )
        return ExternalDependencyCircuitBreaker(service_name, config)

    @staticmethod
    def create_resilient(service_name: str) -> ExternalDependencyCircuitBreaker:
        """Create circuit breaker optimized for resilient operation."""
        config = ModelCircuitBreakerConfig(
            failure_threshold=10,
            failure_rate_threshold=0.6,
            minimum_request_threshold=20,
            recovery_timeout_seconds=120,
            success_threshold=5,
            half_open_max_requests=10,
            request_timeout_seconds=30.0,
            window_size_seconds=300,
            exponential_backoff=True,
            max_backoff_seconds=600,
        )
        return ExternalDependencyCircuitBreaker(service_name, config)

    @staticmethod
    def create_from_environment(
        service_name: str,
        prefix: str | None = None,
    ) -> ExternalDependencyCircuitBreaker:
        """Create circuit breaker with environment-based configuration."""
        env_prefix = prefix or f"CIRCUIT_BREAKER_{service_name.upper()}"
        config = ModelCircuitBreakerConfig.from_environment(prefix=env_prefix)
        return ExternalDependencyCircuitBreaker(service_name, config)


# Global registry for circuit breakers
_circuit_breaker_registry: dict[str, ExternalDependencyCircuitBreaker] = {}


def get_circuit_breaker(
    service_name: str,
    config: ModelCircuitBreakerConfig | None = None,
    create_if_missing: bool = True,
) -> ExternalDependencyCircuitBreaker | None:
    """
    Get or create circuit breaker for a service.

    Args:
        service_name: Name of the service
        config: Optional configuration
        create_if_missing: Create if not found

    Returns:
        Circuit breaker instance or None
    """
    if service_name in _circuit_breaker_registry:
        return _circuit_breaker_registry[service_name]

    if create_if_missing:
        cb = ExternalDependencyCircuitBreaker(service_name, config)
        _circuit_breaker_registry[service_name] = cb
        return cb

    return None


def register_circuit_breaker(
    service_name: str,
    circuit_breaker: ExternalDependencyCircuitBreaker,
) -> None:
    """Register circuit breaker in global registry."""
    _circuit_breaker_registry[service_name] = circuit_breaker
    logger.info(f"Registered circuit breaker for service: {service_name}")


def list_circuit_breakers() -> dict[str, dict[str, Any]]:
    """List all registered circuit breakers with their status."""
    result = {}
    for name, cb in _circuit_breaker_registry.items():
        metrics = cb.get_metrics()
        result[name] = {
            "state": metrics.current_state.value,
            "total_requests": metrics.total_requests,
            "failure_rate": metrics.get_failure_rate(),
            "last_state_change": metrics.last_state_change,
            "requests_in_window": metrics.requests_in_window,
        }
    return result
