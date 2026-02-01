"""
ModelScheduleEffectPayload - Typed payload for SCHEDULE_EFFECT directives.

This module provides the ModelScheduleEffectPayload model for scheduling
effect node execution in the runtime.

Example:
    >>> from omnibase_core.models.runtime.payloads import ModelScheduleEffectPayload
    >>> from omnibase_core.models.common.model_schema_value import ModelSchemaValue
    >>>
    >>> payload = ModelScheduleEffectPayload(
    ...     effect_node_type="http_request",
    ...     effect_input=ModelSchemaValue.create_object({"url": "https://api.example.com"})
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
    "ModelScheduleEffectPayload",
]


class ModelScheduleEffectPayload(ModelDirectivePayloadBase):
    """
    Payload for SCHEDULE_EFFECT directives.

    Used to schedule an effect node for execution. The runtime will locate
    the appropriate effect node by type and invoke it with the provided input.

    Attributes:
        kind: Discriminator field (always "schedule_effect")
        effect_node_type: The type identifier of the effect node to execute
        effect_input: Optional typed input data for the effect node

    Example:
        >>> payload = ModelScheduleEffectPayload(
        ...     effect_node_type="http_request",
        ...     effect_input=ModelSchemaValue.create_object({"url": "https://api.example.com"})
        ... )
    """

    kind: Literal["schedule_effect"] = "schedule_effect"
    effect_node_type: str = Field(
        ...,
        description="The type identifier of the effect node to execute",
        min_length=1,
    )
    effect_input: ModelSchemaValue | None = Field(
        default=None,
        description="Optional typed input data for the effect node",
    )
