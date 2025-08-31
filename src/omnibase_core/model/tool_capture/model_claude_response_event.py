"""
Claude response event model for Tool Capture Events Service.

Represents event data for Claude response generated events.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelClaudeResponseEvent(BaseModel):
    """Event payload for Claude response generated events."""

    event_type: str = Field(
        default="claude_response_generated",
        description="Type of event",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred",
    )
    conversation_id: str = Field(..., description="Associated conversation ID")
    session_id: str | None = Field(None, description="Session identifier")
    response_id: str = Field(..., description="Unique response identifier")
    user_message_id: str = Field(..., description="Associated user message ID")
    has_text_content: bool = Field(..., description="Whether response has text")
    text_length: int = Field(..., description="Length of text content")
    has_tool_requests: bool = Field(..., description="Whether tools were requested")
    tool_count: int = Field(..., description="Number of tool requests")
    model_used: str | None = Field(None, description="Model used")
    tokens_used: int = Field(0, description="Tokens consumed")
    response_time_ms: float = Field(0.0, description="Response time in milliseconds")
    stop_reason: str | None = Field(None, description="Stop reason")
