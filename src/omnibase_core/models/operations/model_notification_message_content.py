from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_message_type import EnumMessageType
from omnibase_core.models.operations.model_message_content_base import (
    ModelMessageContentBase,
)


class ModelNotificationMessageContent(ModelMessageContentBase):
    """Notification message content for event notifications."""

    message_type: Literal[EnumMessageType.NOTIFICATION] = Field(
        default=EnumMessageType.NOTIFICATION,
        description="Notification message type",
    )
    notification_category: str = Field(
        default=..., description="Category of the notification"
    )
    severity_level: str = Field(
        default="info",
        description="Notification severity level",
    )
    action_required: bool = Field(
        default=False,
        description="Whether action is required",
    )
    recipients: list[str] = Field(
        default_factory=list,
        description="Notification recipients",
    )
    delivery_channels: list[str] = Field(
        default_factory=list,
        description="Delivery channels to use",
    )
