"""
ModelCancelExecutionPayload - Typed payload for CANCEL_EXECUTION directives.

This module provides the ModelCancelExecutionPayload model for cancelling
an ongoing or scheduled execution.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.runtime.payloads import ModelCancelExecutionPayload
    >>>
    >>> payload = ModelCancelExecutionPayload(
    ...     execution_id=uuid4(),
    ...     reason="User requested cancellation",
    ...     force=False,
    ...     cleanup_required=True,
    ... )

See Also:
    - omnibase_core.enums.enum_directive_type: EnumDirectiveType values
    - model_directive_payload_union.py: Discriminated union of all payloads
    - model_directive_payload_base.py: Base class for payloads
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from omnibase_core.constants.constants_field_limits import MAX_REASON_LENGTH
from omnibase_core.models.runtime.payloads.model_directive_payload_base import (
    ModelDirectivePayloadBase,
)

__all__ = [
    "ModelCancelExecutionPayload",
]


class ModelCancelExecutionPayload(ModelDirectivePayloadBase):
    """
    Payload for CANCEL_EXECUTION directives.

    Used to cancel an ongoing or scheduled execution. Supports forced
    cancellation and optional cleanup operations.

    Attributes:
        kind: Discriminator field (always "cancel_execution")
        execution_id: UUID of the execution to cancel
        reason: Optional human-readable reason for cancellation
        force: Whether to force cancellation even if operation is in progress
        cleanup_required: Whether cleanup operations should be performed

    Example:
        >>> from uuid import uuid4
        >>> payload = ModelCancelExecutionPayload(
        ...     execution_id=uuid4(),
        ...     reason="User requested cancellation",
        ...     force=False,
        ...     cleanup_required=True,
        ... )
    """

    kind: Literal["cancel_execution"] = "cancel_execution"
    execution_id: UUID = Field(
        ...,
        description="UUID of the execution to cancel",
    )
    reason: str | None = Field(
        default=None,
        description="Optional human-readable reason for cancellation",
        max_length=MAX_REASON_LENGTH,
    )
    force: bool = Field(
        default=False,
        description="Whether to force cancellation even if operation is in progress",
    )
    cleanup_required: bool = Field(
        default=True,
        description="Whether cleanup operations should be performed",
    )
