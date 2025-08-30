"""
Conversation session event model for Tool Capture Events Service.

Represents event data for conversation session lifecycle events.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelConversationSessionEvent(BaseModel):
    """Event payload for conversation session lifecycle events."""

    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the event occurred"
    )
    conversation_id: str = Field(..., description="Associated conversation ID")
    session_id: str = Field(..., description="Session identifier")
    session_type: str = Field(..., description="Type of session")
    total_turns: int = Field(..., description="Total conversation turns")
    total_tokens_used: int = Field(..., description="Total tokens used")
    total_tool_requests: int = Field(..., description="Total tool requests made")
    omnimemory_rules_applied: int = Field(..., description="OmniMemory rules applied")
    context_injection_count: int = Field(
        ..., description="Context injections performed"
    )
    started_at: datetime = Field(..., description="When session started")
    last_activity_at: datetime = Field(..., description="Last activity timestamp")
    ended_at: Optional[datetime] = Field(None, description="When session ended")
    session_duration_minutes: Optional[float] = Field(
        None, description="Session duration in minutes"
    )
