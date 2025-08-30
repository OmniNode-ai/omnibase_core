"""
User message event model for Tool Capture Events Service.

Represents event data for user message received events.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelUserMessageEvent(BaseModel):
    """Event payload for user message received events."""

    event_type: str = Field(
        default="user_message_received", description="Type of event"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the event occurred"
    )
    conversation_id: str = Field(..., description="Associated conversation ID")
    session_id: Optional[str] = Field(None, description="Session identifier")
    message_id: str = Field(..., description="Unique message identifier")
    content_length: int = Field(..., description="Length of message content")
    message_type: str = Field(..., description="Type of message")
    model_requested: Optional[str] = Field(None, description="Model requested")
    has_system_prompt: bool = Field(..., description="Whether system prompt exists")
    request_path: str = Field(..., description="Request path")
    request_method: str = Field(..., description="Request method")
