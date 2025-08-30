"""
Query analysis model for semantic search operations.

Provides strongly-typed query analysis to replace Dict[str, Any] usage.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelQueryAnalysis(BaseModel):
    """
    Analysis of search query.

    Replaces Dict[str, Any] usage in query_analysis fields.
    """

    query_tokens: List[str] = Field(
        default_factory=list, description="Tokenized query terms"
    )

    query_intent: Optional[str] = Field(
        default=None, description="Detected intent of the query"
    )

    key_entities: List[str] = Field(
        default_factory=list, description="Key entities extracted from query"
    )

    query_complexity_score: Optional[float] = Field(
        default=None, description="Complexity score of the query (0-1)"
    )

    semantic_embeddings_used: bool = Field(
        default=False, description="Whether semantic embeddings were used"
    )

    query_expansion_terms: List[str] = Field(
        default_factory=list, description="Terms added during query expansion"
    )

    language_detected: Optional[str] = Field(
        default=None, description="Detected language of the query"
    )

    query_type: Optional[str] = Field(
        default=None, description="Type of query (factual, exploratory, etc.)"
    )

    confidence_score: Optional[float] = Field(
        default=None, description="Confidence in query analysis (0-1)"
    )

    processing_time_ms: Optional[int] = Field(
        default=None, description="Time taken to analyze query in milliseconds"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
