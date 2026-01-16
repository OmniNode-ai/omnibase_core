"""
Typed payload models for runtime directives.

This package provides type-safe payload models for each directive type defined
in EnumDirectiveType, replacing the previous untyped dict[str, Any] approach.

Exports:
    Base:
        - ModelDirectivePayloadBase: Base class for all payloads

    Payload Models:
        - ModelScheduleEffectPayload: For SCHEDULE_EFFECT directives
        - ModelEnqueueHandlerPayload: For ENQUEUE_HANDLER directives
        - ModelRetryWithBackoffPayload: For RETRY_WITH_BACKOFF directives
        - ModelDelayUntilPayload: For DELAY_UNTIL directives
        - ModelCancelExecutionPayload: For CANCEL_EXECUTION directives

    Union Type:
        - ModelDirectivePayload: Discriminated union of all payload types

Example:
    >>> from omnibase_core.models.runtime.payloads import (
    ...     ModelDirectivePayload,
    ...     ModelScheduleEffectPayload,
    ... )
    >>>
    >>> # Create a typed payload
    >>> payload = ModelScheduleEffectPayload(
    ...     effect_node_type="http_request",
    ... )
    >>>
    >>> # Use discriminated union for deserialization
    >>> data = {"kind": "cancel_execution", "execution_id": "..."}
    >>> payload = ModelDirectivePayload.model_validate(data)

See Also:
    - omnibase_core.enums.enum_directive_type: EnumDirectiveType values
    - omnibase_core.models.runtime.model_runtime_directive: ModelRuntimeDirective
"""

# Split payload files
from omnibase_core.models.runtime.payloads.model_cancel_execution_payload import (
    ModelCancelExecutionPayload,
)
from omnibase_core.models.runtime.payloads.model_delay_until_payload import (
    ModelDelayUntilPayload,
)
from omnibase_core.models.runtime.payloads.model_directive_payload_base import (
    ModelDirectivePayloadBase,
)
from omnibase_core.models.runtime.payloads.model_directive_payload_union import (
    ModelDirectivePayload,
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

__all__ = [
    # Base
    "ModelDirectivePayloadBase",
    # Payload Models
    "ModelScheduleEffectPayload",
    "ModelEnqueueHandlerPayload",
    "ModelRetryWithBackoffPayload",
    "ModelDelayUntilPayload",
    "ModelCancelExecutionPayload",
    # Union Type
    "ModelDirectivePayload",
]
