"""
Conversation data models for Tool Capture Storage.

Represents conversation sessions, statistics, and search results.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelConversationSummary(BaseModel):
    """Summary data for a conversation session."""

    session_id: str = Field(..., description="Unique session identifier")
    started_at: datetime = Field(..., description="When the conversation started")
    total_turns: int = Field(..., description="Total number of conversation turns")
    total_tokens_used: int = Field(..., description="Total tokens used in conversation")
    total_tool_requests: int = Field(..., description="Total tool requests made")
    user_messages: int = Field(..., description="Number of user messages")
    claude_responses: int = Field(..., description="Number of Claude responses")


class ModelConversationStatistics(BaseModel):
    """Overall statistics for all conversations."""

    total_sessions: int = Field(
        ..., description="Total number of conversation sessions"
    )
    total_user_messages: int = Field(..., description="Total number of user messages")
    total_claude_responses: int = Field(
        ..., description="Total number of Claude responses"
    )
    total_turns: int = Field(..., description="Total number of conversation turns")
    total_tokens: int = Field(
        ..., description="Total tokens used across all conversations"
    )
    total_tool_requests: int = Field(
        ..., description="Total tool requests across all conversations"
    )
    active_days: int = Field(
        ..., description="Number of days with conversation activity"
    )


class ModelConversationSearchResult(BaseModel):
    """Search result for conversation content."""

    session_id: str = Field(..., description="Unique session identifier")
    started_at: datetime = Field(..., description="When the conversation started")
    turn_number: int = Field(..., description="Turn number within the conversation")
    message_type: str = Field(
        ..., description="Type of message (user_message or claude_response)"
    )
    content_snippet: str = Field(..., description="Snippet of matching content")
    search_rank: Optional[float] = Field(None, description="Search relevance rank")
    total_turns: int = Field(..., description="Total turns in this conversation")
    total_tokens_used: int = Field(
        ..., description="Total tokens used in this conversation"
    )
