"""
Search result model for Universal Conversation Memory System.

Provides proper Pydantic model for search operation results,
replacing the basic SearchResult class with clean, type-safe
ONEX-compliant model architecture.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.memory.model_universal_conversation import \
    ModelConversationChunk


class ModelSearchResult(BaseModel):
    """
    Search result model with proper type safety and validation.

    Replaces the basic SearchResult class with clean Pydantic model
    following ONEX architectural standards.

    Provides structured search results with comprehensive metadata
    and proper validation for conversation similarity search operations.
    """

    chunk: ModelConversationChunk = Field(..., description="Matched conversation chunk")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score between 0.0 and 1.0"
    )
    conversation_id: str = Field(
        ..., description="ID of the conversation containing this chunk"
    )

    # Additional search metadata
    rank: int = Field(default=0, ge=0, description="Result ranking (0-based)")
    highlight_snippet: str = Field(
        default="", description="Highlighted text snippet showing the match"
    )
    search_time_ms: float = Field(
        default=0.0, ge=0.0, description="Time taken for this search in milliseconds"
    )

    class Config:
        """Pydantic configuration for ONEX compliance."""

        validate_assignment = True
        extra = "forbid"  # Strict validation - no extra fields allowed

    def get_relevance_category(self) -> str:
        """Get human-readable relevance category based on similarity score."""
        if self.similarity_score >= 0.9:
            return "Highly Relevant"
        elif self.similarity_score >= 0.7:
            return "Relevant"
        elif self.similarity_score >= 0.5:
            return "Somewhat Relevant"
        else:
            return "Potentially Relevant"
