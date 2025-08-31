"""
ONEX-compliant model for retry policy configuration.

Defines retry behavior for external service calls and task processing.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EnumRetryStrategy(str, Enum):
    """Retry strategy enumeration."""

    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CUSTOM = "custom"


class EnumRetryCondition(str, Enum):
    """Conditions that trigger a retry."""

    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"  # 5xx HTTP status
    RATE_LIMITED = "rate_limited"  # 429 HTTP status
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    CUSTOM_ERROR = "custom_error"


class ModelRetryPolicy(BaseModel):
    """
    Retry policy configuration model.

    Defines how to handle failures and retries for external service calls
    with configurable strategies and conditions.
    """

    service_name: str = Field(
        ...,
        description="Name of the service this policy applies to",
    )
    strategy: EnumRetryStrategy = Field(
        EnumRetryStrategy.EXPONENTIAL_BACKOFF,
        description="Retry strategy to use",
    )

    # Basic retry configuration
    max_attempts: int = Field(3, description="Maximum number of retry attempts")
    base_delay: float = Field(1.0, description="Base delay between retries in seconds")
    max_delay: float = Field(
        60.0,
        description="Maximum delay between retries in seconds",
    )

    # Exponential backoff configuration
    backoff_multiplier: float = Field(
        2.0,
        description="Multiplier for exponential backoff",
    )
    jitter: bool = Field(True, description="Add random jitter to delays")
    jitter_factor: float = Field(0.1, description="Jitter factor (0.0-1.0)")

    # Retry conditions
    retry_on_conditions: list[EnumRetryCondition] = Field(
        default_factory=lambda: [
            EnumRetryCondition.NETWORK_ERROR,
            EnumRetryCondition.TIMEOUT,
            EnumRetryCondition.SERVER_ERROR,
        ],
        description="Conditions that should trigger a retry",
    )

    # HTTP-specific configuration
    retry_on_status_codes: list[int] = Field(
        default_factory=lambda: [500, 502, 503, 504, 429],
        description="HTTP status codes that should trigger a retry",
    )

    # Custom delay sequence (for CUSTOM strategy)
    custom_delays: list[float] | None = Field(
        None,
        description="Custom delay sequence in seconds (for CUSTOM strategy)",
    )

    # Circuit breaker integration
    circuit_breaker_enabled: bool = Field(
        True,
        description="Whether to integrate with circuit breaker",
    )

    # Timeout configuration
    operation_timeout: float = Field(
        30.0,
        description="Timeout for individual operation attempts",
    )
    total_timeout: float = Field(
        300.0,
        description="Total timeout including all retry attempts",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "service_name": "ollama_api",
                "strategy": "exponential_backoff",
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 60.0,
                "backoff_multiplier": 2.0,
                "jitter": True,
                "jitter_factor": 0.1,
                "retry_on_conditions": ["network_error", "timeout", "server_error"],
                "retry_on_status_codes": [500, 502, 503, 504, 429],
                "circuit_breaker_enabled": True,
                "operation_timeout": 30.0,
                "total_timeout": 300.0,
            },
        }
