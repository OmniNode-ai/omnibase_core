from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.models.common.model_request_metadata import ModelRequestMetadata
from omnibase_core.models.context import (
    ModelAuthorizationContext,
    ModelSessionContext,
)
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
    session_context: ModelSessionContext | None = Field(
        default=None,
        description="User session context (session_id, device, locale, etc.)",
    )
    request_metadata: ModelRequestMetadata | None = Field(
        default=None,
        description="Request metadata (trace_id, source, environment, etc.)",
    )
    authorization_context: ModelAuthorizationContext | None = Field(
        default=None,
        description="User authorization context (auth method, roles, permissions)",
    )
