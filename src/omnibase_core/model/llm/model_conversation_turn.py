"""
Conversation turn model for tracking individual conversation interactions.

Provides strongly-typed representation of a single conversational turn
with comprehensive metadata and quality tracking.
"""

from pydantic import Field

from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState


class ModelConversationTurn(ModelOnexInputState):
    """
    A single turn in a conversational interaction.

    Provides comprehensive tracking of user query, system response,
    and associated metadata for conversation history management.
    """

    timestamp: float = Field(..., description="Unix timestamp of the conversation turn")
    user_query: str = Field(..., description="Original user query")
    enhanced_query: str = Field(..., description="Enhanced query used for retrieval")
    system_response: str = Field(..., description="System-generated response")
    sources_used: list[str] = Field(
        default_factory=list,
        description="Sources referenced in the response",
    )
    model_used: str = Field(..., description="LLM model used for generation")
    response_time_ms: int = Field(
        ...,
        ge=0,
        description="Response generation time in milliseconds",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality score for the response (0.0 to 1.0)",
    )
