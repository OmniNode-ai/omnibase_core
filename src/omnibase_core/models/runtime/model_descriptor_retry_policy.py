"""
Descriptor Retry Policy Model.

Defines retry policy configuration for handler descriptors embedded in contracts.
Part of the three-layer architecture: Profile -> Descriptor -> Contract.

Related:
    - OMN-1125: Default Profile Factory for Contracts
    - ModelHandlerBehavior: Parent handler behavior model
    - ModelRetryPolicy: Full-featured retry policy with execution tracking

.. versionadded:: 0.4.0
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelDescriptorRetryPolicy",
]


class ModelDescriptorRetryPolicy(BaseModel):
    """Simplified retry policy configuration for handler descriptors.

    This is a lightweight configuration model for embedding in handler
    descriptors. For full-featured retry policies with execution tracking,
    see ModelRetryPolicy in omnibase_core.models.infrastructure.

    Attributes:
        enabled: Whether retry is enabled for this handler.
        max_retries: Maximum number of retry attempts (0-10).
        backoff_strategy: Strategy for calculating delay between retries.
        base_delay_ms: Initial delay between retries in milliseconds.
        max_delay_ms: Maximum delay cap for backoff strategies.
        jitter_factor: Randomization factor as fraction of delay (0.0-0.5).

    Example:
        >>> policy = ModelDescriptorRetryPolicy(
        ...     enabled=True,
        ...     max_retries=3,
        ...     backoff_strategy="exponential",
        ...     base_delay_ms=1000,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(
        default=True,
        description="Whether retry is enabled for this handler",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
    )
    backoff_strategy: Literal["fixed", "exponential", "linear"] = Field(
        default="exponential",
        description="Strategy for calculating delay between retries",
    )
    base_delay_ms: int = Field(
        default=1000,
        ge=100,
        le=60000,
        description="Initial delay between retries in milliseconds",
    )
    max_delay_ms: int = Field(
        default=30000,
        ge=100,
        le=300000,
        description="Maximum delay cap for backoff strategies in milliseconds",
    )
    jitter_factor: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Randomization factor as fraction of delay",
    )
