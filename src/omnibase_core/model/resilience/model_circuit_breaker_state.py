"""
ONEX-compliant model for circuit breaker state.

Circuit breaker pattern implementation for distributed system resilience.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EnumCircuitBreakerState(str, Enum):
    """Circuit breaker state enumeration."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ModelCircuitBreakerState(BaseModel):
    """
    Circuit breaker state model for resilience management.

    Tracks failure counts, state transitions, and recovery attempts
    following ONEX standards for distributed system reliability.
    """

    service_name: str = Field(..., description="Name of the protected service")
    current_state: EnumCircuitBreakerState = Field(
        EnumCircuitBreakerState.CLOSED, description="Current circuit breaker state"
    )
    failure_count: int = Field(0, description="Current consecutive failure count")
    failure_threshold: int = Field(5, description="Failures needed to open circuit")
    recovery_timeout: int = Field(
        60, description="Seconds to wait before trying half-open"
    )
    success_threshold: int = Field(
        3, description="Successes needed to close from half-open"
    )

    last_failure_time: Optional[datetime] = Field(
        None, description="Timestamp of last failure"
    )
    last_success_time: Optional[datetime] = Field(
        None, description="Timestamp of last success"
    )
    state_changed_at: datetime = Field(
        default_factory=datetime.now, description="When state last changed"
    )

    consecutive_successes: int = Field(
        0, description="Consecutive successes in half-open state"
    )
    total_requests: int = Field(0, description="Total requests processed")
    total_failures: int = Field(0, description="Total failures encountered")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "service_name": "ollama_client",
                "current_state": "closed",
                "failure_count": 2,
                "failure_threshold": 5,
                "recovery_timeout": 60,
                "success_threshold": 3,
                "last_failure_time": "2025-07-30T12:00:00Z",
                "last_success_time": "2025-07-30T12:05:00Z",
                "state_changed_at": "2025-07-30T12:00:00Z",
                "consecutive_successes": 0,
                "total_requests": 150,
                "total_failures": 8,
            }
        }
