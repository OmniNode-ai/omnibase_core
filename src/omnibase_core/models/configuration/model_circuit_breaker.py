"""
ModelCircuitBreaker - Circuit breaker configuration for load balancing

Circuit breaker model for implementing fault tolerance and preventing
cascade failures in load balancing systems.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, Field

from .model_circuit_breaker_metadata import ModelCircuitBreakerMetadata


class ModelCircuitBreaker(BaseModel):
    """
    Circuit breaker configuration for load balancing fault tolerance.

    This model implements the circuit breaker pattern to prevent cascade
    failures by monitoring node health and temporarily disabling failing nodes.

    Thread Safety:
        This class is NOT thread-safe. Mutable state includes:
        - failure_count, success_count, total_requests, half_open_requests
        - state, last_failure_time, last_state_change

        Concurrent access from multiple threads may cause:
        - Counter corruption (missed increments)
        - Incorrect state transitions (race between check and update)
        - False circuit trips or resets

        Mitigation Options:
        1. **Thread-local instances** (recommended): Each thread gets its own
           circuit breaker via threading.local()
        2. **Synchronized wrapper**: Wrap all methods with threading.Lock
        3. **Single-threaded access**: Ensure only one thread accesses the instance

        See docs/guides/THREADING.md for detailed examples of thread-safe
        circuit breaker patterns including ThreadSafeCircuitBreaker wrapper.

    Example (thread-safe usage):
        >>> import threading
        >>> thread_local = threading.local()
        >>>
        >>> def get_circuit_breaker(service_name: str) -> ModelCircuitBreaker:
        ...     if not hasattr(thread_local, 'breakers'):
        ...         thread_local.breakers = {}
        ...     if service_name not in thread_local.breakers:
        ...         thread_local.breakers[service_name] = ModelCircuitBreaker()
        ...     return thread_local.breakers[service_name]
    """

    enabled: bool = Field(
        default=True,
        description="Whether circuit breaker is enabled",
    )

    failure_threshold: int = Field(
        default=5,
        description="Number of failures before opening circuit",
        ge=1,
        le=100,
    )

    success_threshold: int = Field(
        default=3,
        description="Number of successes to close circuit from half-open",
        ge=1,
        le=20,
    )

    timeout_seconds: int = Field(
        default=60,
        description="Timeout before attempting to close circuit",
        ge=10,
        le=3600,
    )

    window_size_seconds: int = Field(
        default=120,
        description="Time window for failure counting",
        ge=30,
        le=3600,
    )

    half_open_max_requests: int = Field(
        default=3,
        description="Maximum requests allowed in half-open state",
        ge=1,
        le=10,
    )

    failure_rate_threshold: float = Field(
        default=0.5,
        description="Failure rate threshold (0.0-1.0) to open circuit",
        ge=0.0,
        le=1.0,
    )

    minimum_request_threshold: int = Field(
        default=10,
        description="Minimum requests before failure rate is considered",
        ge=1,
        le=1000,
    )

    slow_call_duration_threshold_ms: int | None = Field(
        default=None,
        description="Duration threshold for slow calls in milliseconds",
        ge=100,
        le=60000,
    )

    slow_call_rate_threshold: float | None = Field(
        default=None,
        description="Slow call rate threshold (0.0-1.0) to open circuit",
        ge=0.0,
        le=1.0,
    )

    state: str = Field(
        default="closed",
        description="Current circuit breaker state",
        pattern="^(closed|open|half_open)$",
    )

    last_failure_time: datetime | None = Field(
        default=None,
        description="Timestamp of last failure",
    )

    last_state_change: datetime | None = Field(
        default=None,
        description="Timestamp of last state change",
    )

    failure_count: int = Field(
        default=0,
        description="Current failure count in window",
        ge=0,
    )

    success_count: int = Field(
        default=0,
        description="Current success count in half-open state",
        ge=0,
    )

    total_requests: int = Field(
        default=0,
        description="Total requests in current window",
        ge=0,
    )

    half_open_requests: int = Field(
        default=0,
        description="Requests made in half-open state",
        ge=0,
    )

    circuit_breaker_metadata: ModelCircuitBreakerMetadata | None = Field(
        default=None,
        description="Additional circuit breaker metadata",
    )

    # =========================================================================
    # Protocol Conformance Properties and Methods
    # =========================================================================
    # These properties and methods enable ModelCircuitBreaker to conform to
    # ProtocolCircuitBreaker for dependency injection and duck typing.
    # See: src/omnibase_core/protocols/compute/protocol_circuit_breaker.py

    @property
    def is_open(self) -> bool:
        """
        Check if circuit breaker is currently open (rejecting requests).

        This property enables conformance to ProtocolCircuitBreaker.
        Returns True only when state is "open", not during half-open testing.

        Returns:
            True if circuit is open and requests should be rejected,
            False if circuit is closed or half-open.

        Related:
            - ProtocolCircuitBreaker.is_open: Protocol definition
            - state: Underlying state field
            - get_current_state(): State with automatic transitions
        """
        return self.state == "open"

    def should_allow_request(self) -> bool:
        """Check if a request should be allowed through the circuit breaker"""
        if not self.enabled:
            return True

        current_time = datetime.now(UTC)

        # Clean up old data outside window
        self._cleanup_old_data(current_time)

        if self.state == "closed":
            return True
        if self.state == "open":
            # Check if timeout has elapsed to transition to half-open
            if self._should_transition_to_half_open(current_time):
                self._transition_to_half_open()
                return True
            return False
        if self.state == "half_open":
            # Allow limited requests in half-open state
            return self.half_open_requests < self.half_open_max_requests

        return False

    def record_success(self) -> None:
        """Record a successful request"""
        if not self.enabled:
            return

        current_time = datetime.now(UTC)
        self.total_requests += 1

        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()

        self._cleanup_old_data(current_time)

    def record_failure(self, correlation_id: UUID | None = None) -> None:
        """
        Record a failed request.

        This method enables conformance to ProtocolCircuitBreaker.

        Args:
            correlation_id: Optional UUID for correlating failures across
                distributed systems. Currently unused but accepted for
                protocol conformance. Future implementations may use this
                for logging, tracing, or distributed circuit breaker
                coordination.
        """
        # Note: correlation_id is accepted for protocol conformance but
        # not currently used. Future enhancement: log with correlation_id
        _ = correlation_id  # Unused parameter - protocol conformance

        if not self.enabled:
            return

        current_time = datetime.now(UTC)
        self.failure_count += 1
        self.total_requests += 1
        self.last_failure_time = current_time

        if self.state == "half_open":
            # Any failure in half-open transitions back to open
            self._transition_to_open()
        elif self.state == "closed":
            # Check if we should open the circuit
            if self._should_open_circuit():
                self._transition_to_open()

        self._cleanup_old_data(current_time)

    def record_slow_call(self, duration_ms: int) -> None:
        """Record a slow call (if slow call detection is enabled)"""
        if not self.enabled or not self.slow_call_duration_threshold_ms:
            return

        if duration_ms >= self.slow_call_duration_threshold_ms:
            # Treat slow calls as failures for circuit breaker purposes
            self.record_failure()

    def get_current_state(self) -> str:
        """Get current circuit breaker state with potential state transitions"""
        if not self.enabled:
            return "disabled"

        current_time = datetime.now(UTC)

        if self.state == "open" and self._should_transition_to_half_open(current_time):
            self._transition_to_half_open()

        return self.state

    def get_failure_rate(self) -> float:
        """Calculate current failure rate"""
        if self.total_requests == 0:
            return 0.0
        return self.failure_count / self.total_requests

    def force_open(self) -> None:
        """Force circuit breaker to open state"""
        self._transition_to_open()

    def force_close(self) -> None:
        """Force circuit breaker to closed state"""
        self._transition_to_closed()

    def reset_state(self) -> None:
        """Reset circuit breaker to initial state"""
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.half_open_requests = 0
        self.last_failure_time = None
        self.last_state_change = datetime.now(UTC)

    def reset(self) -> None:
        """
        Manually reset circuit breaker to closed state.

        This method provides ProtocolCircuitBreaker conformance by
        delegating to reset_state(). Both methods are functionally
        equivalent and can be used interchangeably.

        Resets all counters and state to initial values:
        - State transitions to closed
        - Failure and success counters reset to zero
        - Any timing-related state is cleared

        Use Cases:
            - Manual recovery after fixing underlying issues
            - Testing and development scenarios
            - Forced recovery when automatic recovery isn't working

        Warning:
            Calling reset() while underlying issues persist may lead to
            immediate re-opening of the circuit. Use with caution.

        Related:
            - ProtocolCircuitBreaker.reset: Protocol definition
            - reset_state(): Internal method (identical behavior)
        """
        self.reset_state()

    def _should_open_circuit(self) -> bool:
        """Check if circuit should be opened based on failures"""
        # Need minimum requests before considering failure rate
        if self.total_requests < self.minimum_request_threshold:
            return False

        # Check absolute failure count
        if self.failure_count >= self.failure_threshold:
            return True

        # Check failure rate
        failure_rate = self.get_failure_rate()
        return failure_rate >= self.failure_rate_threshold

    def _should_transition_to_half_open(self, current_time: datetime) -> bool:
        """Check if circuit should transition from open to half-open"""
        if not self.last_state_change:
            return True

        time_since_open = current_time - self.last_state_change
        return time_since_open.total_seconds() >= self.timeout_seconds

    def _transition_to_open(self) -> None:
        """Transition circuit breaker to open state"""
        self.state = "open"
        self.last_state_change = datetime.now(UTC)
        self.half_open_requests = 0
        self.success_count = 0

    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to half-open state"""
        self.state = "half_open"
        self.last_state_change = datetime.now(UTC)
        self.half_open_requests = 0
        self.success_count = 0

    def _transition_to_closed(self) -> None:
        """Transition circuit breaker to closed state"""
        self.state = "closed"
        self.last_state_change = datetime.now(UTC)
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.half_open_requests = 0

    def _cleanup_old_data(self, current_time: datetime) -> None:
        """Clean up old failure data outside the time window"""
        if not self.last_failure_time:
            return

        window_start = current_time - timedelta(seconds=self.window_size_seconds)

        # If last failure was outside the window, reset counters
        if self.last_failure_time < window_start:
            self.failure_count = 0
            self.total_requests = 0

    @classmethod
    def create_fast_fail(cls) -> "ModelCircuitBreaker":
        """Create circuit breaker for fast failure detection"""
        return cls(
            enabled=True,
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=30,
            window_size_seconds=60,
            failure_rate_threshold=0.3,
            minimum_request_threshold=5,
        )

    @classmethod
    def create_resilient(cls) -> "ModelCircuitBreaker":
        """Create circuit breaker for resilient operation"""
        return cls(
            enabled=True,
            failure_threshold=10,
            success_threshold=5,
            timeout_seconds=120,
            window_size_seconds=300,
            failure_rate_threshold=0.6,
            minimum_request_threshold=20,
        )

    @classmethod
    def create_disabled(cls) -> "ModelCircuitBreaker":
        """Create disabled circuit breaker"""
        return cls(enabled=False)
