"""
Strongly-typed event payload structure.

Replaces dict[str, Any] usage in event payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelEventPayload(BaseModel):
    """
    Strongly-typed event payload.

    Replaces dict[str, Any] with structured event payload model.
    """

    event_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Event data with proper typing"
    )
    context: dict[str, str] = Field(
        default_factory=dict, description="Event context information"
    )
    attributes: dict[str, str] = Field(
        default_factory=dict, description="Event attributes"
    )
    source_info: dict[str, str] = Field(
        default_factory=dict, description="Event source information"
    )
    routing_info: dict[str, str] = Field(
        default_factory=dict, description="Event routing information"
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelEventPayload"]
