"""
OmniMemory trigger event model for Tool Capture Events Service.

Represents event data for OmniMemory context processing triggers.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelOmniMemoryTriggerEvent(BaseModel):
    """Event payload for OmniMemory context processing triggers."""

    event_type: str = Field(
        default="omnimemory_context_trigger",
        description="Type of event",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred",
    )
    conversation_id: str = Field(..., description="Associated conversation ID")
    session_id: str | None = Field(None, description="Session identifier")
    trigger_reason: str = Field(..., description="Reason for triggering")
    claude_response_id: str = Field(..., description="Claude response ID")
    user_message_id: str = Field(..., description="User message ID")
    tool_requests: list[str] = Field(
        default_factory=list,
        description="Tool requests that triggered processing",
    )
    model_used: str | None = Field(None, description="Model used for response")
    priority: str = Field(..., description="Processing priority")
