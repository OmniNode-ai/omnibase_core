"""
Conversation turn event model for Tool Capture Events Service.

Represents event data for conversation turn completed events.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelConversationTurnEvent(BaseModel):
    """Event payload for conversation turn completed events."""

    event_type: str = Field(
        default="conversation_turn_completed",
        description="Type of event",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred",
    )
    conversation_id: str = Field(..., description="Associated conversation ID")
    session_id: str | None = Field(None, description="Session identifier")
    turn_id: str = Field(..., description="Unique turn identifier")
    turn_number: int = Field(..., description="Turn number in conversation")
    user_message_id: str = Field(..., description="User message ID")
    claude_response_id: str = Field(..., description="Claude response ID")
    turn_successful: bool = Field(..., description="Whether turn was successful")
    context_injected: bool = Field(..., description="Whether context was injected")
    rules_applied_count: int = Field(..., description="Number of rules applied")
    duration_ms: int = Field(0, description="Turn duration in milliseconds")
