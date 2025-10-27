from typing import Any

from pydantic import Field

from .model_eventrouting import ModelEventRouting

__all__ = [
    "ModelEventRouting",
    "ModelRetryPolicy",
]

"""
Event Routing Model - ONEX Standards Compliant.

Model for event routing configuration in the ONEX event-driven architecture system.
"""

from pydantic import BaseModel


class ModelRetryPolicy(BaseModel):
    """
    Strongly-typed retry policy configuration.

    Replaces dict[str, int | bool] pattern with proper type safety.
    """

    max_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0,
        le=10,
    )

    initial_delay_ms: int = Field(
        default=1000,
        description="Initial delay before first retry in milliseconds",
        ge=100,
        le=60000,
    )

    backoff_multiplier: int = Field(
        default=2,
        description="Exponential backoff multiplier",
        ge=1,
        le=10,
    )

    max_delay_ms: int = Field(
        default=30000,
        description="Maximum delay between retries in milliseconds",
        ge=1000,
        le=300000,
    )

    enabled: bool = Field(
        default=True,
        description="Whether retry policy is enabled",
    )

    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry on timeout errors",
    )
