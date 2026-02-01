"""
ModelEnqueueHandlerPayload - Typed payload for ENQUEUE_HANDLER directives.

This module provides the ModelEnqueueHandlerPayload model for enqueuing
handlers for asynchronous execution in the runtime.

Example:
    >>> from omnibase_core.models.runtime.payloads import ModelEnqueueHandlerPayload
    >>> from omnibase_core.models.common.model_schema_value import ModelSchemaValue
    >>>
    >>> payload = ModelEnqueueHandlerPayload(
    ...     handler_args=ModelSchemaValue.create_object({"task_id": "123"}),
    ...     priority=5,
    ...     queue_name="high-priority"
    ... )

See Also:
    - omnibase_core.enums.enum_directive_type: EnumDirectiveType values
    - model_directive_payload_union.py: Discriminated union of all payloads
    - model_directive_payload_base.py: Base class for payloads
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.runtime.payloads.model_directive_payload_base import (
    ModelDirectivePayloadBase,
)

__all__ = [
    "ModelEnqueueHandlerPayload",
]


class ModelEnqueueHandlerPayload(ModelDirectivePayloadBase):
    """
    Payload for ENQUEUE_HANDLER directives.

    Used to enqueue a handler for asynchronous execution with optional
    priority and queue targeting.

    Attributes:
        kind: Discriminator field (always "enqueue_handler")
        handler_args: Arguments to pass to the handler (typed as ModelSchemaValue)
        priority: Execution priority (1=lowest, 10=highest)
        queue_name: Optional specific queue to use for execution

    Example:
        >>> payload = ModelEnqueueHandlerPayload(
        ...     handler_args=ModelSchemaValue.create_object({"task_id": "123"}),
        ...     priority=5,
        ...     queue_name="high-priority"
        ... )
    """

    kind: Literal["enqueue_handler"] = "enqueue_handler"
    handler_args: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.create_object({}),
        description="Arguments to pass to the handler",
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Execution priority (1=lowest, 10=highest)",
    )
    queue_name: str | None = Field(
        default=None,
        description="Optional specific queue to use for execution",
    )
