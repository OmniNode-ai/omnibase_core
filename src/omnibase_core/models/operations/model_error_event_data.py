from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.models.operations.model_event_data_base import ModelEventDataBase


class ModelErrorEventData(ModelEventDataBase):
    """Error event data."""

    event_type: Literal[EnumEventType.ERROR] = Field(
        default=EnumEventType.ERROR,
        description="Error event type",
    )
    error_type: str = Field(default=..., description="Type of error")
    error_message: str = Field(default=..., description="Error message")
    stack_trace: str = Field(default="", description="Error stack trace")
    recovery_actions: list[str] = Field(
        default_factory=list,
        description="Suggested recovery actions",
    )
    impact_assessment: dict[str, str] = Field(
        default_factory=dict,
        description="Error impact assessment",
    )
