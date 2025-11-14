from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.models.operations.model_event_data_base import ModelEventDataBase


class ModelUserEventData(ModelEventDataBase):
    """User-initiated event data."""

    event_type: Literal[EnumEventType.USER] = Field(
        default=EnumEventType.USER,
        description="User event type",
    )
    user_action: str = Field(
        default=..., description="User action that triggered the event"
    )
    session_context: dict[str, str] = Field(
        default_factory=dict,
        description="User session context",
    )
    request_metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Request metadata",
    )
    authorization_context: dict[str, str] = Field(
        default_factory=dict,
        description="User authorization context",
    )
