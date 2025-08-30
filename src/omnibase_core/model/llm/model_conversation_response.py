"""
Conversation response model for conversation management operations.

Provides strongly-typed response models for conversation interactions
including answers, metadata, and session information.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState


class ModelConversationResponse(ModelOnexInputState):
    """
    Response model for conversation interactions.

    Provides comprehensive response information including generated answer,
    metadata, and conversation context for conversation management.
    """

    answer: str = Field(..., description="Generated answer text")
    user_query: str = Field(..., description="Original user query")
    enhanced_query: str = Field(..., description="Enhanced query used for processing")
    sources_used: list[str] = Field(
        default_factory=list,
        description="Sources referenced in the answer",
    )
    model_used: str = Field(..., description="Model used for generation")
    response_time_ms: int = Field(
        ...,
        ge=0,
        description="Response generation time in milliseconds",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality score for the response",
    )
    session_id: str = Field(..., description="Conversation session identifier")
    turn_number: int = Field(..., ge=1, description="Turn number in the conversation")
    streaming: bool = Field(default=False, description="Whether response was streamed")


class ModelSessionSummary(ModelOnexInputState):
    """
    Session summary model for conversation session information.

    Provides comprehensive session metadata and statistics for
    conversation management and tracking.
    """

    session_id: str = Field(..., description="Session identifier")
    total_turns: int = Field(
        ...,
        ge=0,
        description="Total number of conversation turns",
    )
    session_duration_ms: int = Field(
        ...,
        ge=0,
        description="Session duration in milliseconds",
    )
    average_response_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Average response time",
    )
    total_tokens_used: int = Field(
        ...,
        ge=0,
        description="Total tokens used in session",
    )
    primary_topics: list[str] = Field(
        default_factory=list,
        description="Primary topics discussed in session",
    )
    session_summary: str = Field(..., description="Summary of session content")
    user_satisfaction_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="User satisfaction score if available",
    )


class ModelSessionInfo(BaseModel):
    """
    Session information model for session listing.

    Provides basic session information for session management
    and selection operations.
    """

    session_id: str = Field(..., description="Session identifier")
    created_at: str = Field(..., description="Session creation timestamp")
    last_activity: str = Field(..., description="Last activity timestamp")
    total_turns: int = Field(..., ge=0, description="Total conversation turns")
    session_summary: str = Field(..., description="Brief session summary")
