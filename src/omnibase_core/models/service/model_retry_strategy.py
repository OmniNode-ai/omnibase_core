"""
Retry Strategy Model

Type-safe retry strategy configuration.
"""

from pydantic import BaseModel, Field


class ModelRetryStrategy(BaseModel):
    """
    Type-safe retry strategy configuration.

    Defines retry behavior for operations with backoff and timeout settings.
    """

    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0,
        le=10,
    )

    backoff_multiplier: float = Field(
        default=1.5,
        description="Backoff multiplier for exponential backoff",
        gt=1.0,
        le=5.0,
    )

    max_backoff: int = Field(
        default=30,
        description="Maximum backoff time in seconds",
        ge=1,
        le=300,
    )

    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry on timeout errors",
    )

    initial_backoff: float = Field(
        default=1.0,
        description="Initial backoff time in seconds",
        gt=0,
        le=60,
    )

    jitter: bool = Field(
        default=True, description="Whether to add jitter to backoff times"
    )
