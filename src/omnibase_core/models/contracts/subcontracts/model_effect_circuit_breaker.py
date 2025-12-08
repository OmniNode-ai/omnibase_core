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
    Effect-specific circuit breaker configuration (simplified view).

    Note: For full circuit breaker configuration with advanced features (sliding windows,
    failure rates, slow call detection), use ModelCircuitBreakerSubcontract from:
        omnibase_core.models.contracts.subcontracts.model_circuit_breaker_subcontract

    This simplified version provides effect-specific defaults optimized for
    common I/O operation patterns. For runtime state management, compose with
    the existing ModelCircuitBreaker infrastructure.

    SCOPE: Process-local only in v1.0.
    Keyed by operation correlation_id (stable identity).
    NOT shared across threads - NodeEffect instances must be isolated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=False)
    failure_threshold: int = Field(default=5, ge=1, le=100)
    success_threshold: int = Field(default=2, ge=1, le=10)
    timeout_ms: int = Field(default=60000, ge=1000, le=600000)
    half_open_requests: int = Field(default=3, ge=1, le=10)
