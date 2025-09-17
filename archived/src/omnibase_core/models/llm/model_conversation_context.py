"""
Conversation context model for maintaining state across conversational turns.

Provides strongly-typed conversation state management for RAG systems
with comprehensive metadata and quality tracking.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_onex_base_state import ModelOnexInputState


class ModelRetrievedDocument(BaseModel):
    """Model representing a retrieved document with metadata."""

    content: str = Field(..., description="Document content text")
    source: str = Field(..., description="Source file or reference")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional document metadata",
    )


class ModelConversationContext(ModelOnexInputState):
    """
    Conversation context for maintaining state across conversational turns.

    Provides comprehensive tracking of conversation state, retrieved documents,
    response quality, and performance metrics for RAG systems.
    """

    conversation_id: str = Field(..., description="Unique conversation identifier")
    user_query: str = Field(..., description="Original user query")
    enhanced_query: str = Field(..., description="Enhanced query for retrieval")
    retrieved_documents: list[ModelRetrievedDocument] = Field(
        default_factory=list,
        description="Documents retrieved for context",
    )
    llm_response: str = Field(..., description="Generated LLM response")
    sources_used: list[str] = Field(
        default_factory=list,
        description="Source references used in response",
    )
    model_used: str = Field(..., description="LLM model used for generation")
    retrieval_time_ms: int = Field(
        ...,
        ge=0,
        description="Document retrieval time in milliseconds",
    )
    generation_time_ms: int = Field(
        ...,
        ge=0,
        description="Response generation time in milliseconds",
    )
    total_time_ms: int = Field(
        ...,
        ge=0,
        description="Total processing time in milliseconds",
    )
    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Response quality score (0.0 to 1.0)",
    )
