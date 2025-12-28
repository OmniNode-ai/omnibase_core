from pydantic import Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS, TIMEOUT_LONG_MS, TIMEOUT_MIN_MS

from .model_eventrouting import ModelEventRouting

__all__ = [
    "ModelEventRouting",
    "ModelRetryPolicy",
]

"""
Event Routing Model.

Model for event routing configuration in the ONEX event-driven architecture system.
"""

from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelRetryPolicy(BaseModel):
    """
    Strongly-typed retry policy configuration.

    Replaces dict[str, int | bool] pattern with proper type safety.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

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
        default=TIMEOUT_DEFAULT_MS,
        description="Maximum delay between retries in milliseconds",
        ge=TIMEOUT_MIN_MS,
        le=TIMEOUT_LONG_MS,  # Max 5 minutes (TIMEOUT_LONG_MS)
    )

    enabled: bool = Field(
        default=True,
        description="Whether retry policy is enabled",
    )

    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry on timeout errors",
    )
