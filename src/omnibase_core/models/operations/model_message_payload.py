"""
Strongly-typed message payload structure.

Replaces dict[str, Any] usage in message payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_event_metadata import ModelEventMetadata


class ModelMessagePayload(BaseModel):
    """
    Strongly-typed message payload.

    Replaces dict[str, Any] with structured message payload model.
    """

    message_id: UUID = Field(
        default_factory=uuid4, description="Unique message identifier (UUID format)"
    )
    message_type: str = Field(..., description="Type of message")
    content: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Structured message content with proper typing",
    )
    headers: dict[str, str] = Field(default_factory=dict, description="Message headers")
    metadata: ModelEventMetadata = Field(
        default_factory=lambda: ModelEventMetadata(
            event_id=uuid4(), event_type="message", source="system"
        ),
        description="Event metadata for the message",
    )


# Export for use
__all__ = ["ModelMessagePayload"]
