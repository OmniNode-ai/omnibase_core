"""
Conversation session model for managing conversational RAG sessions.

Provides strongly-typed session management with user preferences,
conversation history, and session metadata.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_conversation_status import EnumConversationStatus
from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState
from omnibase_core.model.llm.model_conversation_context import \
    ModelConversationContext


class ModelUserPreferences(BaseModel):
    """Model for user preferences in conversational sessions."""

    preferred_response_length: str = Field(
        default="medium", description="Preferred response length (short, medium, long)"
    )
    technical_level: str = Field(
        default="intermediate",
        description="Technical detail level (beginner, intermediate, expert)",
    )
    include_sources: bool = Field(
        default=True, description="Whether to include source citations"
    )
    enable_streaming: bool = Field(
        default=False, description="Whether to enable streaming responses"
    )
    preferred_model: Optional[str] = Field(
        default=None, description="Preferred LLM model if specified"
    )


class ModelConversationSession(ModelOnexInputState):
    """
    Conversation session model for managing conversational RAG sessions.

    Provides comprehensive session management including conversation history,
    user preferences, and session lifecycle tracking.
    """

    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(
        default=None, description="User identifier if authenticated"
    )
    status: EnumConversationStatus = Field(
        default=EnumConversationStatus.INITIALIZED, description="Current session status"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Session creation timestamp"
    )
    last_activity: datetime = Field(
        default_factory=datetime.now, description="Last activity timestamp"
    )
    conversation_history: List[ModelConversationContext] = Field(
        default_factory=list, description="History of conversation turns"
    )
    user_preferences: ModelUserPreferences = Field(
        default_factory=ModelUserPreferences,
        description="User preferences for the session",
    )
    total_queries: int = Field(
        default=0, ge=0, description="Total number of queries in session"
    )
    total_tokens_used: int = Field(
        default=0, ge=0, description="Total tokens used in session"
    )
    average_response_time_ms: Optional[float] = Field(
        default=None, ge=0.0, description="Average response time in milliseconds"
    )
    session_summary: Optional[str] = Field(
        default=None, description="Summary of session content"
    )
