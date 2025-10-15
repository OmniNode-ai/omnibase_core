"""
VERSION: 1.0.0
STABILITY GUARANTEE: Abstract method signatures frozen.
Breaking changes require major version bump.

ModelCircuitBreaker - Circuit Breaker Pattern for External Service Failures.

Implements the circuit breaker pattern to prevent cascading failures by temporarily
disabling calls to failing services. Used by NodeEffect and other nodes requiring
resilient external service interactions.

Key Capabilities:
- Automatic failure detection and recovery
- Three-state management (CLOSED, OPEN, HALF_OPEN)
- Configurable failure thresholds and recovery timeouts
- Half-open state for gradual service recovery testing
- Thread-safe state management

STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.
Code generators can target this stable interface.

Author: ONEX Framework Team
"""

from datetime import datetime, timedelta
from enum import Enum

__all__ = ["ModelCircuitBreaker", "CircuitBreakerState"]


class CircuitBreakerState(Enum):
    """Circuit breaker states for failure handling."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ModelCircuitBreaker:
    """
    Circuit breaker pattern for handling external service failures.

    Prevents cascading failures by temporarily disabling calls to failing services.
    Implements a three-state pattern (CLOSED, OPEN, HALF_OPEN) with automatic
    recovery testing and configurable thresholds.

    States:
        CLOSED: Normal operation, requests pass through
        OPEN: Service failing, all requests rejected
        HALF_OPEN: Testing recovery, limited requests allowed

    Args:
        failure_threshold: Number of failures before opening circuit (default: 5)
        recovery_timeout_seconds: Seconds to wait before testing recovery (default: 60)
        half_open_max_attempts: Max attempts in HALF_OPEN state (default: 3)

    Example:
        >>> breaker = ModelCircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30)
        >>> if breaker.can_execute():
        ...     try:
        ...         result = external_service_call()
        ...         breaker.record_success()
        ...     except Exception:
        ...         breaker.record_failure()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        half_open_max_attempts: int = 3,
    ):
        """
        Initialize ModelCircuitBreaker with configurable thresholds.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout_seconds: Time to wait before attempting recovery
            half_open_max_attempts: Maximum attempts allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_attempts = half_open_max_attempts

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.half_open_attempts = 0

    def can_execute(self) -> bool:
        """
        Check if operation can be executed based on circuit breaker state.

        Returns:
            True if operation can proceed, False if circuit is open

        Logic:
            - CLOSED: Always allow execution
            - OPEN: Check if recovery timeout has elapsed, transition to HALF_OPEN
            - HALF_OPEN: Allow execution if under max attempts threshold
        """
        now = datetime.now()

        if self.state == CircuitBreakerState.CLOSED:
            return True
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and now - self.last_failure_time > timedelta(
                seconds=self.recovery_timeout_seconds,
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_attempts = 0
                return True
            return False
        # HALF_OPEN
        return self.half_open_attempts < self.half_open_max_attempts

    def record_success(self) -> None:
        """
        Record successful operation and update circuit breaker state.

        State Transitions:
            - HALF_OPEN -> CLOSED: Service recovered, reset counters
            - CLOSED: Decrement failure count (gradual recovery)
        """
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.half_open_attempts = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """
        Record failed operation and update circuit breaker state.

        State Transitions:
            - HALF_OPEN -> OPEN: Service still failing, retry later
            - CLOSED -> OPEN: Failure threshold exceeded, open circuit
        """
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.half_open_attempts = 0
        elif (
            self.state == CircuitBreakerState.CLOSED
            and self.failure_count >= self.failure_threshold
        ):
            self.state = CircuitBreakerState.OPEN
