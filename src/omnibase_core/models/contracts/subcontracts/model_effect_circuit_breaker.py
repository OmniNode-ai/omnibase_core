"""
Effect Circuit Breaker Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Effect-specific circuit breaker configuration (simplified view).
Provides effect-specific defaults optimized for common I/O operation patterns.

Implements: OMN-524
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectCircuitBreaker"]


class ModelEffectCircuitBreaker(BaseModel):
    """
    Effect-specific circuit breaker configuration for protecting external I/O operations.

    Circuit breakers prevent cascading failures by temporarily blocking requests to
    failing external services. When failures exceed the threshold, the circuit "opens"
    and rejects requests immediately without attempting the operation. After a timeout,
    the circuit enters "half-open" state and allows a limited number of test requests
    to determine if the service has recovered.

    This is a simplified configuration optimized for common I/O patterns. For advanced
    features like sliding windows, failure rates, and slow call detection, use
    ModelCircuitBreakerSubcontract from:
        omnibase_core.models.contracts.subcontracts.model_circuit_breaker_subcontract

    Attributes:
        enabled: Whether circuit breaker protection is active. Defaults to False,
            requiring explicit opt-in for each operation.
        failure_threshold: Number of consecutive failures before opening the circuit.
            Range: 1-100. Default: 5.
        success_threshold: Number of consecutive successes in half-open state
            required to close the circuit. Range: 1-10. Default: 2.
        timeout_ms: Duration in milliseconds the circuit stays open before
            transitioning to half-open state. Range: 1000-600000ms. Default: 60000ms (1 min).
        half_open_requests: Maximum concurrent requests allowed in half-open state
            to test if the service has recovered. Range: 1-10. Default: 3.

    Thread Safety:
        NOT thread-safe. NodeEffect instances must be isolated per thread.
        Circuit state is process-local only in v1.0, keyed by operation correlation_id.

    Example:
        >>> circuit_breaker = ModelEffectCircuitBreaker(
        ...     enabled=True,
        ...     failure_threshold=3,
        ...     success_threshold=2,
        ...     timeout_ms=30000,
        ...     half_open_requests=1,
        ... )

    See Also:
        - ModelCircuitBreakerSubcontract: Full-featured circuit breaker configuration
        - ModelEffectRetryPolicy: Retry behavior that works with circuit breakers
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Whether circuit breaker protection is active for this operation",
    )
    failure_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Consecutive failures before opening the circuit",
    )
    success_threshold: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Consecutive successes in half-open state to close the circuit",
    )
    timeout_ms: int = Field(
        default=60000,
        ge=1000,
        le=600000,
        description="Duration in ms the circuit stays open before testing recovery",
    )
    half_open_requests: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max concurrent requests allowed in half-open state",
    )
