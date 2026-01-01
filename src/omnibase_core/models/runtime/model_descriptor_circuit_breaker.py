"""
Descriptor Circuit Breaker Model.

Defines circuit breaker configuration for handler descriptors embedded in contracts.
Part of the three-layer architecture: Profile -> Descriptor -> Contract.

Related:
    - OMN-1125: Default Profile Factory for Contracts
    - ModelHandlerBehavior: Parent handler behavior model
    - ModelCircuitBreaker: Full-featured circuit breaker with state management

.. versionadded:: 0.4.0
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelDescriptorCircuitBreaker",
]


class ModelDescriptorCircuitBreaker(BaseModel):
    """Simplified circuit breaker configuration for handler descriptors.

    This is a lightweight configuration model for embedding in handler
    descriptors. For full-featured circuit breakers with state management,
    see ModelCircuitBreaker in omnibase_core.models.configuration.

    Circuit breakers prevent cascading failures by temporarily blocking
    requests to failing services. When failures exceed the threshold, the
    circuit "opens" and rejects requests immediately.

    Attributes:
        enabled: Whether circuit breaker protection is active.
        failure_threshold: Number of failures before opening the circuit.
        success_threshold: Successes in half-open state to close the circuit.
        timeout_ms: Duration the circuit stays open before testing recovery.
        half_open_requests: Max concurrent requests allowed in half-open state.

    Example:
        >>> circuit_breaker = ModelDescriptorCircuitBreaker(
        ...     enabled=True,
        ...     failure_threshold=5,
        ...     success_threshold=2,
        ...     timeout_ms=60000,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(
        default=False,
        description="Whether circuit breaker protection is active",
    )
    failure_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of failures before opening the circuit",
    )
    success_threshold: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Successes in half-open state required to close the circuit",
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
