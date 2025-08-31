"""
Answer generation result model for LLM-powered response generation.

Provides strongly-typed results for answer generation operations
including generated content, quality metrics, and metadata.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState
from omnibase_core.model.llm.model_conversation_context import ModelRetrievedDocument


class ModelAnswerCandidate(BaseModel):
    """Model representing a single answer candidate with quality metrics."""

    answer_text: str = Field(..., description="Generated answer text")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Answer confidence score",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Answer quality score",
    )
    source_coverage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of sources utilized in answer",
    )
    model_used: str = Field(..., description="Model used for generation")
    generation_time_ms: int = Field(
        ...,
        ge=0,
        description="Generation time in milliseconds",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional answer metadata",
    )


class ModelAnswerGenerationResult(ModelOnexInputState):
    """
    Answer generation result model for LLM-powered response generation.

    Provides comprehensive results for answer generation operations including
    generated answers, quality metrics, and source attribution.
    """

    user_query: str = Field(..., description="Original user query")
    enhanced_query: str = Field(..., description="Enhanced query used for generation")
    context_documents: list[ModelRetrievedDocument] = Field(
        default_factory=list,
        description="Documents used as context for generation",
    )
    answer_candidates: list[ModelAnswerCandidate] = Field(
        default_factory=list,
        description="Generated answer candidates with quality scores",
    )
    selected_answer: str = Field(..., description="Final selected answer")
    sources_cited: list[str] = Field(
        default_factory=list,
        description="Sources cited in the final answer",
    )
    overall_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the generated answer",
    )
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Total processing time in milliseconds",
    )
    tokens_used: int | None = Field(
        default=None,
        ge=0,
        description="Total tokens used for generation",
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback generation was used",
    )
    generation_metadata: dict = Field(
        default_factory=dict,
        description="Additional generation metadata",
    )
