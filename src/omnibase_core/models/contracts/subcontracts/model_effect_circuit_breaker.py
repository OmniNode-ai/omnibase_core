"""
Effect Circuit Breaker Model.

Effect-specific circuit breaker configuration (simplified view).
Provides effect-specific defaults optimized for common I/O operation patterns.
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

    Configuration vs Runtime:
        This model defines CONTRACT configuration (what goes in YAML subcontracts).
        At runtime, NodeEffect.get_circuit_breaker() creates ModelCircuitBreaker
        instances using ModelCircuitBreaker.create_resilient() which has different
        defaults optimized for production:

        | Setting            | This Model  | create_resilient() |
        |--------------------|-------------|-------------------|
        | failure_threshold  | 5           | 10                |
        | success_threshold  | 2           | 5                 |
        | timeout            | 60000ms     | 120s              |

        When an operation has circuit_breaker configuration in its subcontract,
        those values override the resilient defaults. When no configuration is
        provided, resilient defaults apply. Specify values in YAML for tighter
        failure detection or more lenient thresholds as needed.

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
        Circuit state is process-local only in v1.0, keyed by operation_id.

    Example:
        >>> from omnibase_core.constants import TIMEOUT_DEFAULT_MS
        >>> circuit_breaker = ModelEffectCircuitBreaker(
        ...     enabled=True,
        ...     failure_threshold=3,
        ...     success_threshold=2,
        ...     timeout_ms=TIMEOUT_DEFAULT_MS,  # 30 seconds
        ...     half_open_requests=1,
        ... )

    See Also:
        - ModelCircuitBreakerSubcontract: Full-featured circuit breaker configuration
        - ModelEffectRetryPolicy: Retry behavior that works with circuit breakers
        - ModelCircuitBreaker.create_resilient: Runtime circuit breaker factory
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

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
