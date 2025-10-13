from pydantic import Field

"""
Circuit Breaker Model - ONEX Standards Compliant.

Individual model for circuit breaker configuration.
Part of the Routing Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


class ModelCircuitBreaker(BaseModel):
    """
    Circuit breaker configuration.

    Defines circuit breaker behavior for fault tolerance,
    including failure thresholds and recovery policies.
    """

    enabled: bool = Field(
        default=True,
        description="Enable circuit breaker functionality",
    )

    failure_threshold: int = Field(
        default=5,
        description="Failures before opening circuit",
        ge=1,
    )

    success_threshold: int = Field(
        default=3,
        description="Successes before closing circuit",
        ge=1,
    )

    timeout_ms: int = Field(default=60000, description="Circuit open timeout", ge=1000)

    half_open_max_calls: int = Field(
        default=3,
        description="Max calls in half-open state",
        ge=1,
    )

    failure_rate_threshold: float = Field(
        default=0.5,
        description="Failure rate threshold",
        ge=0.0,
        le=1.0,
    )

    minimum_calls: int = Field(
        default=10,
        description="Minimum calls before evaluation",
        ge=1,
    )

    slow_call_duration_ms: int = Field(
        default=60000,
        description="Duration for slow call detection",
        ge=1000,
    )

    slow_call_rate_threshold: float = Field(
        default=0.6,
        description="Slow call rate threshold",
        ge=0.0,
        le=1.0,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
