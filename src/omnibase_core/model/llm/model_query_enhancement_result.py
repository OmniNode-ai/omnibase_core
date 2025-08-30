"""
Query enhancement result model for LLM-powered query processing.

Provides strongly-typed results for query enhancement operations
including intent detection and enhancement metadata.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_query_type import EnumQueryType
from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState


class ModelQueryIntent(BaseModel):
    """Model representing detected query intent and classification."""

    primary_intent: EnumQueryType = Field(..., description="Primary detected intent")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for intent",
    )
    secondary_intents: list[EnumQueryType] = Field(
        default_factory=list,
        description="Secondary detected intents",
    )
    complexity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Query complexity score (0.0 = simple, 1.0 = complex)",
    )


class ModelQueryEnhancementResult(ModelOnexInputState):
    """
    Query enhancement result model for LLM-powered query processing.

    Provides comprehensive results for query enhancement operations including
    enhanced query text, intent detection, and processing metadata.
    """

    original_query: str = Field(..., description="Original user query")
    enhanced_query: str = Field(..., description="Enhanced query for retrieval")
    query_intent: ModelQueryIntent = Field(
        ...,
        description="Detected query intent and classification",
    )
    keywords_extracted: list[str] = Field(
        default_factory=list,
        description="Key terms extracted from query",
    )
    suggested_filters: list[str] = Field(
        default_factory=list,
        description="Suggested filters for retrieval",
    )
    enhancement_reasoning: str | None = Field(
        default=None,
        description="Explanation of enhancement decisions",
    )
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Enhancement processing time in milliseconds",
    )
    model_used: str = Field(..., description="Model used for enhancement")
    enhancement_quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Quality score for enhancement (0.0 to 1.0)",
    )
