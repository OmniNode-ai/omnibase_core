"""
ModelRetryWithBackoffPayload - Typed payload for RETRY_WITH_BACKOFF directives.

This module provides the ModelRetryWithBackoffPayload model for configuring
retry behavior with exponential backoff for failed operations.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.runtime.payloads import ModelRetryWithBackoffPayload
    >>>
    >>> payload = ModelRetryWithBackoffPayload(
    ...     operation_id=uuid4(),
    ...     current_attempt=2,
    ...     backoff_multiplier=2.0,
    ...     initial_backoff_ms=500,
    ...     max_backoff_ms=60000,
    ... )

See Also:
    - omnibase_core.enums.enum_directive_type: EnumDirectiveType values
    - model_directive_payload_union.py: Discriminated union of all payloads
    - model_directive_payload_base.py: Base class for payloads
"""

from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.payloads.model_directive_payload_base import (
    ModelDirectivePayloadBase,
)

__all__ = [
    "ModelRetryWithBackoffPayload",
]


class ModelRetryWithBackoffPayload(ModelDirectivePayloadBase):
    """
    Payload for RETRY_WITH_BACKOFF directives.

    Used to configure retry behavior with exponential backoff for failed operations.
    Supports configurable backoff multiplier, initial/max delays, and optional jitter.

    Attributes:
        kind: Discriminator field (always "retry_with_backoff")
        operation_id: UUID of the operation to retry
        current_attempt: Current attempt number (0-indexed)
        backoff_multiplier: Multiplier for exponential backoff
        max_backoff_ms: Maximum backoff delay in milliseconds
        initial_backoff_ms: Initial backoff delay in milliseconds
        jitter: Whether to add random jitter to backoff

    Example:
        >>> from uuid import uuid4
        >>> payload = ModelRetryWithBackoffPayload(
        ...     operation_id=uuid4(),
        ...     current_attempt=2,
        ...     backoff_multiplier=2.0,
        ...     initial_backoff_ms=500,
        ...     max_backoff_ms=60000,
        ... )
    """

    kind: Literal["retry_with_backoff"] = "retry_with_backoff"
    operation_id: UUID = Field(
        ...,
        description="UUID of the operation to retry",
    )
    current_attempt: int = Field(
        default=0,
        ge=0,
        description="Current attempt number (0-indexed)",
    )
    backoff_multiplier: float = Field(
        default=1.5,
        gt=1.0,
        le=10.0,
        description="Multiplier for exponential backoff (must be > 1.0)",
    )
    max_backoff_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        ge=1000,
        le=3600000,
        description="Maximum backoff delay in milliseconds (1s to 1h)",
    )
    initial_backoff_ms: int = Field(
        default=1000,
        ge=100,
        le=60000,
        description="Initial backoff delay in milliseconds (100ms to 60s)",
    )
    jitter: bool = Field(
        default=True,
        description="Whether to add random jitter to backoff",
    )

    @model_validator(mode="after")
    def _validate_backoff_bounds(self) -> Self:
        """
        Validate that initial_backoff_ms does not exceed max_backoff_ms.

        This ensures that the initial backoff delay is always less than or equal
        to the maximum backoff delay, preventing invalid configurations.

        Raises:
            ModelOnexError: If initial_backoff_ms > max_backoff_ms
        """
        if self.initial_backoff_ms > self.max_backoff_ms:
            raise ModelOnexError(
                message=(
                    f"initial_backoff_ms ({self.initial_backoff_ms}) cannot exceed "
                    f"max_backoff_ms ({self.max_backoff_ms})"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                initial_backoff_ms=self.initial_backoff_ms,
                max_backoff_ms=self.max_backoff_ms,
            )
        return self
