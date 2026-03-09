# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Retry Policy Contract Model.

Declarative retry policy for ONEX handler lifecycle operations — configuring
retry behavior for startup and teardown without referencing any runtime
retry mechanism or concrete handler implementation.

See Also:
    - OMN-4221: Extract HandlerLifecycleContract into omnibase_core
    - ModelHandlerLifecycleContract: Lifecycle contract that composes this retry policy
    - ModelRetrySubcontract: General-purpose retry subcontract for ONEX nodes

.. versionadded:: 1.9.0
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelRetryPolicyContract(BaseModel):
    """
    Declarative retry policy for handler lifecycle operations.

    Configures retry behavior for startup and teardown operations.
    Does not reference any runtime retry mechanism or handler implementation.

    Attributes:
        max_retries: Maximum number of retry attempts (0 disables retries).
        base_delay_seconds: Initial delay between retries in seconds.
        backoff_strategy: Strategy for computing delay between retries.
        max_delay_seconds: Upper cap on retry delay to prevent unbounded waits.

    Immutability:
        The model is frozen. Use ``model_copy(update={...})`` to derive variants.

    Example:
        >>> policy = ModelRetryPolicyContract(
        ...     max_retries=3,
        ...     base_delay_seconds=1.0,
        ...     backoff_strategy="exponential",
        ...     max_delay_seconds=30.0,
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts (0 = retries disabled)",
    )

    base_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=300.0,
        description="Initial delay between retry attempts in seconds",
    )

    backoff_strategy: Literal["fixed", "linear", "exponential"] = Field(
        default="exponential",
        description=(
            "Strategy for computing delay between retries: "
            "'fixed' (constant delay), 'linear' (delay * attempt), "
            "'exponential' (delay * 2^attempt)"
        ),
    )

    max_delay_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=3600.0,
        description="Upper bound on retry delay to prevent unbounded waits",
    )


__all__ = ["ModelRetryPolicyContract"]
