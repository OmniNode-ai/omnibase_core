from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.operations.model_event_attribute_info import (
    ModelEventAttributeInfo,
)
from omnibase_core.models.operations.model_event_context_info import (
    ModelEventContextInfo,
)
from omnibase_core.models.operations.model_event_source_info import ModelEventSourceInfo


class ModelEventDataBase(BaseModel):
    """Base event data with discriminator."""

    event_type: EnumEventType = Field(
        default=..., description="Event type discriminator"
    )
    context: ModelEventContextInfo = Field(
        default_factory=lambda: ModelEventContextInfo(),
        description="Structured event context information",
    )
    attributes: ModelEventAttributeInfo = Field(
        default_factory=lambda: ModelEventAttributeInfo(),
        description="Structured event attributes",
    )
    source_info: ModelEventSourceInfo = Field(
        default_factory=lambda: ModelEventSourceInfo(),
        description="Structured event source information",
    )
