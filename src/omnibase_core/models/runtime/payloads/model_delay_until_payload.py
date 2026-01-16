"""
ModelDelayUntilPayload - Typed payload for DELAY_UNTIL directives.

This module provides the ModelDelayUntilPayload model for delaying
execution of an operation until a specific point in time.

Example:
    >>> from datetime import datetime, UTC, timedelta
    >>> from uuid import uuid4
    >>> from omnibase_core.models.runtime.payloads import ModelDelayUntilPayload
    >>>
    >>> payload = ModelDelayUntilPayload(
    ...     execute_at=datetime.now(UTC) + timedelta(minutes=5),
    ...     operation_id=uuid4(),
    ...     reason="Rate limit cooldown",
    ... )

See Also:
    - omnibase_core.enums.enum_directive_type: EnumDirectiveType values
    - model_directive_payload_union.py: Discriminated union of all payloads
    - model_directive_payload_base.py: Base class for payloads
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, Field

from omnibase_core.constants.constants_field_limits import MAX_REASON_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.payloads.model_directive_payload_base import (
    ModelDirectivePayloadBase,
)

__all__ = [
    "ModelDelayUntilPayload",
]


def _validate_timezone_aware(value: datetime) -> datetime:
    """
    Validate that a datetime value is timezone-aware.

    Args:
        value: The datetime to validate

    Returns:
        The validated datetime value

    Raises:
        ModelOnexError: If the datetime is naive (has no timezone info)
    """
    if value.tzinfo is None:
        raise ModelOnexError(
            message="execute_at must be timezone-aware (have tzinfo set)",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return value


class ModelDelayUntilPayload(ModelDirectivePayloadBase):
    """
    Payload for DELAY_UNTIL directives.

    Used to delay execution of an operation until a specific point in time.
    Useful for scheduled tasks, rate limiting, or time-based coordination.

    Attributes:
        kind: Discriminator field (always "delay_until")
        execute_at: Timezone-aware datetime when execution should occur.
            Accepts any timezone (UTC, local, or other), not just UTC.
            A naive datetime (without tzinfo) will raise a validation error.
        operation_id: UUID of the operation to delay
        reason: Optional human-readable reason for the delay

    Example:
        >>> from datetime import datetime, UTC, timedelta
        >>> from uuid import uuid4
        >>> payload = ModelDelayUntilPayload(
        ...     execute_at=datetime.now(UTC) + timedelta(minutes=5),
        ...     operation_id=uuid4(),
        ...     reason="Rate limit cooldown",
        ... )
    """

    kind: Literal["delay_until"] = "delay_until"
    execute_at: Annotated[datetime, AfterValidator(_validate_timezone_aware)] = Field(
        ...,
        description="Timezone-aware datetime when execution should occur",
    )
    operation_id: UUID = Field(
        ...,
        description="UUID of the operation to delay",
    )
    reason: str | None = Field(
        default=None,
        description="Optional human-readable reason for the delay",
        max_length=MAX_REASON_LENGTH,
    )
