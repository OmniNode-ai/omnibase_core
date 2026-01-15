"""
ModelCircuitBreaker - Circuit breaker configuration for load balancing

Circuit breaker model for implementing fault tolerance and preventing
cascade failures in load balancing systems.

# ============================================================================
# PR #328 Context: Why This Fix Is Included in the Evidence Models PR
# ============================================================================
#
# This file contains fixes for a LATENT BUG that existed before the evidence
# models work but was EXPOSED when running tests with pytest-xdist parallel
# execution.
#
# The Problem:
# ------------
# ModelCircuitBreaker has a forward reference to ModelCircuitBreakerMetadata,
# which in turn has a forward reference to ModelCustomFields. When pytest-xdist
# runs tests in parallel across multiple worker processes, each worker imports
# modules independently and in potentially different orders. This caused
# Pydantic to fail with "ModelCustomFields is not fully defined" errors because
# the forward references were not resolved before validation.
#
# Why It Appeared in Evidence Model Tests:
# ----------------------------------------
# The evidence model tests (ModelEvidenceSummary, etc.) import modules that
# transitively depend on ModelCircuitBreaker. When these tests run in parallel
# with pytest-xdist (using `-n auto` or `-n 4` workers), the import order
# becomes non-deterministic. This exposed the latent forward reference bug
# that was hidden when tests ran sequentially.
#
# The Fix:
# --------
# 1. Added _ensure_models_rebuilt() with thread-safe double-checked locking
# 2. Override __new__ to trigger rebuild before Pydantic validation
# 3. Override model_validate() and model_validate_json() for class method calls
#
# This ensures forward references are resolved regardless of import order,
# making the model safe for parallel test execution across worker processes.
#
# Related Issue: OMN-1195 (Evidence Summary Model implementation)
# ============================================================================
"""

import threading
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState

from .model_circuit_breaker_metadata import ModelCircuitBreakerMetadata

# Lazy model rebuild flag - forward references are resolved on first use, not at import
_models_rebuilt = False
_rebuild_lock = threading.Lock()


def _ensure_models_rebuilt(circuit_breaker_cls: type[BaseModel] | None = None) -> None:
    """Ensure models are rebuilt to resolve forward references (lazy initialization).

    This function implements lazy model rebuild to avoid importing ModelCustomFields
    at module load time. The rebuild only happens on first ModelCircuitBreaker
    instantiation, improving import performance when the model isn't used.

    The pattern:
    1. Module-level flag tracks if rebuild has occurred
    2. This function is called via __new__ on first instantiation
    3. The rebuild resolves ModelCircuitBreakerMetadata's forward reference to ModelCustomFields
    4. Then rebuilds ModelCircuitBreaker to pick up the resolved metadata type
    5. Subsequent instantiations skip the rebuild (flag is already True)

    Args:
        circuit_breaker_cls: The ModelCircuitBreaker class to rebuild. Must be provided
            on first call to properly resolve the forward reference chain.

    Thread Safety:
        This function is thread-safe. It uses double-checked locking to ensure that
        concurrent first-instantiation calls safely coordinate the rebuild. The pattern:
        1. Fast path: Check flag without lock (subsequent calls return immediately)
        2. Acquire lock only when rebuild might be needed
        3. Re-check flag inside lock to handle race conditions
        4. Perform rebuild and set flag atomically within lock
    """
    global _models_rebuilt
    if _models_rebuilt:  # Fast path - no lock needed
        return

    with _rebuild_lock:
        if (
            _models_rebuilt
        ):  # Double-check after acquiring lock  # type: ignore[unreachable]
            return  # type: ignore[unreachable]

        from omnibase_core.models.services.model_custom_fields import (  # noqa: F401
            ModelCustomFields,
        )

        # First rebuild the metadata model to resolve its forward reference
        ModelCircuitBreakerMetadata.model_rebuild()
        # Then rebuild the circuit breaker model to pick up the resolved metadata
        if circuit_breaker_cls is not None:
            circuit_breaker_cls.model_rebuild()
        _models_rebuilt = True


class ModelCircuitBreaker(BaseModel):
    """
    Circuit breaker configuration for load balancing fault tolerance.

    This model implements the circuit breaker pattern to prevent cascade
    failures by monitoring node health and temporarily disabling failing nodes.

    Thread Safety:
        This class IS thread-safe. All state-modifying operations are protected
        by an internal threading.Lock. This includes:
        - Counter updates (failure_count, success_count, total_requests, half_open_requests)
        - State transitions (closed -> open -> half_open -> closed)
        - All public methods that modify state

        The lock is stored as a private attribute and is automatically created
        when the model is instantiated.

    Example:
        >>> breaker = ModelCircuitBreaker()
        >>> # Safe to use from multiple threads
        >>> breaker.record_failure()
        >>> breaker.record_success()
        >>> if breaker.should_allow_request():
        ...     # Execute request
        ...     pass
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        arbitrary_types_allowed=True,  # Required for threading.Lock private attr
    )

    def __new__(cls, **_data: object) -> "ModelCircuitBreaker":
        """Override __new__ to trigger lazy model rebuild before Pydantic validation.

        Pydantic validates model completeness before calling model_validator,
        so we must trigger the rebuild in __new__ which runs first.

        Args:
            **_data: Keyword arguments passed to Pydantic (handled by __init__).
        """
        _ensure_models_rebuilt(cls)
        return super().__new__(cls)

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> "ModelCircuitBreaker":
        """Validate data and create a model instance.

        This override ensures forward references are resolved before validation,
        enabling lazy initialization while supporting model_validate() calls.

        Args:
            obj: The object to validate.
            strict: Whether to enforce strict validation.
            extra: How to handle extra fields.
            from_attributes: Whether to extract data from object attributes.
            context: Additional context to pass to validators.
            by_alias: Whether to populate by alias.
            by_name: Whether to populate by field name.

        Returns:
            A validated ModelCircuitBreaker instance.
        """
        _ensure_models_rebuilt(cls)
        return super().model_validate(
            obj,
            strict=strict,
            extra=extra,
            from_attributes=from_attributes,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> "ModelCircuitBreaker":
        """Validate JSON data and create a model instance.

        This override ensures forward references are resolved before validation,
        enabling lazy initialization while supporting model_validate_json() calls.

        Args:
            json_data: The JSON data to validate.
            strict: Whether to enforce strict validation.
            extra: How to handle extra fields.
            context: Additional context to pass to validators.
            by_alias: Whether to populate by alias.
            by_name: Whether to populate by field name.

        Returns:
            A validated ModelCircuitBreaker instance.
        """
        _ensure_models_rebuilt(cls)
        return super().model_validate_json(
            json_data,
            strict=strict,
            extra=extra,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    # Private lock for thread-safe operations
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

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

    state: EnumCircuitBreakerState = Field(
        default=EnumCircuitBreakerState.CLOSED,
        description="Current circuit breaker state",
    )

    @field_validator("state", mode="before")
    @classmethod
    def _normalize_state(cls, v: str | EnumCircuitBreakerState) -> str:
        """Accept both string and enum, normalize to string for serialization."""
        if isinstance(v, EnumCircuitBreakerState):
            return v.value
        valid_states = {
            EnumCircuitBreakerState.CLOSED.value,
            EnumCircuitBreakerState.OPEN.value,
            EnumCircuitBreakerState.HALF_OPEN.value,
        }
        if isinstance(v, str) and v in valid_states:
            return v
        # error-ok: Pydantic field_validator requires ValueError
        raise ValueError(
            f"Invalid circuit breaker state: {v!r}. Valid states: {sorted(valid_states)}"
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
        return self.state == EnumCircuitBreakerState.OPEN

    def should_allow_request(self) -> bool:
        """Check if a request should be allowed through the circuit breaker"""
        if not self.enabled:
            return True

        with self._lock:
            current_time = datetime.now(UTC)

            # Clean up old data outside window
            self._cleanup_old_data_unlocked(current_time)

            if self.state == EnumCircuitBreakerState.CLOSED:
                return True
            if self.state == EnumCircuitBreakerState.OPEN:
                # Check if timeout has elapsed to transition to half-open
                if self._should_transition_to_half_open(current_time):
                    self._transition_to_half_open_unlocked()
                    return True
                return False
            if self.state == EnumCircuitBreakerState.HALF_OPEN:
                # Allow limited requests in half-open state
                if self.half_open_requests < self.half_open_max_requests:
                    self.half_open_requests += 1
                    return True
            return False

    def record_success(self) -> None:
        """Record a successful request"""
        if not self.enabled:
            return

        with self._lock:
            current_time = datetime.now(UTC)
            self.total_requests += 1

            if self.state == EnumCircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._transition_to_closed_unlocked()

            self._cleanup_old_data_unlocked(current_time)

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

        with self._lock:
            current_time = datetime.now(UTC)
            self.failure_count += 1
            self.total_requests += 1
            self.last_failure_time = current_time

            if self.state == EnumCircuitBreakerState.HALF_OPEN:
                # Any failure in half-open transitions back to open
                self._transition_to_open_unlocked()
            elif self.state == EnumCircuitBreakerState.CLOSED:
                # Check if we should open the circuit
                if self._should_open_circuit():
                    self._transition_to_open_unlocked()

            self._cleanup_old_data_unlocked(current_time)

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

        with self._lock:
            current_time = datetime.now(UTC)

            if (
                self.state == EnumCircuitBreakerState.OPEN
                and self._should_transition_to_half_open(current_time)
            ):
                self._transition_to_half_open_unlocked()

            return self.state.value

    def get_failure_rate(self) -> float:
        """Calculate current failure rate"""
        with self._lock:
            return self._get_failure_rate_unlocked()

    def _get_failure_rate_unlocked(self) -> float:
        """Calculate current failure rate (internal, no lock)."""
        if self.total_requests == 0:
            return 0.0
        return self.failure_count / self.total_requests

    def force_open(self) -> None:
        """Force circuit breaker to open state"""
        with self._lock:
            self._transition_to_open_unlocked()

    def force_close(self) -> None:
        """Force circuit breaker to closed state"""
        with self._lock:
            self._transition_to_closed_unlocked()

    def reset_state(self) -> None:
        """Reset circuit breaker to initial state"""
        with self._lock:
            self._reset_state_unlocked()

    def _reset_state_unlocked(self) -> None:
        """Reset circuit breaker to initial state (internal, no lock)."""
        self.state = EnumCircuitBreakerState.CLOSED
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
        """Check if circuit should be opened based on failures.

        Note: This method is called from within locked sections, so it
        must not acquire the lock itself to avoid deadlock.
        """
        # Need minimum requests before considering failure rate
        if self.total_requests < self.minimum_request_threshold:
            return False

        # Check absolute failure count
        if self.failure_count >= self.failure_threshold:
            return True

        # Check failure rate (use unlocked version to avoid deadlock)
        failure_rate = self._get_failure_rate_unlocked()
        return failure_rate >= self.failure_rate_threshold

    def _should_transition_to_half_open(self, current_time: datetime) -> bool:
        """Check if circuit should transition from open to half-open"""
        if not self.last_state_change:
            return True

        time_since_open = current_time - self.last_state_change
        return time_since_open.total_seconds() >= self.timeout_seconds

    def _transition_to_open(self) -> None:
        """Transition circuit breaker to open state (thread-safe)."""
        with self._lock:
            self._transition_to_open_unlocked()

    def _transition_to_open_unlocked(self) -> None:
        """Transition circuit breaker to open state (internal, no lock)."""
        self.state = EnumCircuitBreakerState.OPEN
        self.last_state_change = datetime.now(UTC)
        self.half_open_requests = 0
        self.success_count = 0

    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to half-open state (thread-safe)."""
        with self._lock:
            self._transition_to_half_open_unlocked()

    def _transition_to_half_open_unlocked(self) -> None:
        """Transition circuit breaker to half-open state (internal, no lock)."""
        self.state = EnumCircuitBreakerState.HALF_OPEN
        self.last_state_change = datetime.now(UTC)
        self.half_open_requests = 0
        self.success_count = 0

    def _transition_to_closed(self) -> None:
        """Transition circuit breaker to closed state (thread-safe)."""
        with self._lock:
            self._transition_to_closed_unlocked()

    def _transition_to_closed_unlocked(self) -> None:
        """Transition circuit breaker to closed state (internal, no lock)."""
        self.state = EnumCircuitBreakerState.CLOSED
        self.last_state_change = datetime.now(UTC)
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.half_open_requests = 0

    def _cleanup_old_data(self, current_time: datetime) -> None:
        """Clean up old failure data outside the time window (thread-safe)."""
        with self._lock:
            self._cleanup_old_data_unlocked(current_time)

    def _cleanup_old_data_unlocked(self, current_time: datetime) -> None:
        """Clean up old failure data outside the time window (internal, no lock)."""
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
