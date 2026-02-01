"""
Discriminated union type for directive payloads.

This module provides the ModelDirectivePayload type alias, which is a
discriminated union of all directive payload types. The `kind` field
serves as the discriminator, enabling Pydantic to automatically select
the correct payload model during deserialization.

Usage:
    >>> from omnibase_core.models.runtime.payloads import ModelDirectivePayload
    >>>
    >>> # Pydantic will automatically deserialize to correct type based on 'kind'
    >>> data = {"kind": "schedule_effect", "effect_node_type": "http_request"}
    >>> payload = ModelDirectivePayload.model_validate(data)  # Type: ModelScheduleEffectPayload

Discriminator Values:
    - "schedule_effect" -> ModelScheduleEffectPayload
    - "enqueue_handler" -> ModelEnqueueHandlerPayload
    - "retry_with_backoff" -> ModelRetryWithBackoffPayload
    - "delay_until" -> ModelDelayUntilPayload
    - "cancel_execution" -> ModelCancelExecutionPayload

See Also:
    - Split payload files: model_*_payload.py
    - omnibase_core.enums.enum_directive_type: EnumDirectiveType values
"""

from typing import Annotated

from pydantic import Field

# Split payload files
from omnibase_core.models.runtime.payloads.model_cancel_execution_payload import (
    ModelCancelExecutionPayload,
)
from omnibase_core.models.runtime.payloads.model_delay_until_payload import (
    ModelDelayUntilPayload,
)
from omnibase_core.models.runtime.payloads.model_enqueue_handler_payload import (
    ModelEnqueueHandlerPayload,
)
from omnibase_core.models.runtime.payloads.model_retry_with_backoff_payload import (
    ModelRetryWithBackoffPayload,
)
from omnibase_core.models.runtime.payloads.model_schedule_effect_payload import (
    ModelScheduleEffectPayload,
)

__all__ = ["ModelDirectivePayload"]


# Discriminated union of all directive payload types.
# The 'kind' field serves as the discriminator for automatic type selection.
ModelDirectivePayload = Annotated[
    ModelScheduleEffectPayload
    | ModelEnqueueHandlerPayload
    | ModelRetryWithBackoffPayload
    | ModelDelayUntilPayload
    | ModelCancelExecutionPayload,
    Field(discriminator="kind"),
]
