"""
Query analysis model for semantic search operations.

Provides strongly-typed query analysis to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelQueryAnalysis(BaseModel):
    """
    Analysis of search query.

    Replaces Dict[str, Any] usage in query_analysis fields.
    """

    query_tokens: list[str] = Field(
        default_factory=list,
        description="Tokenized query terms",
    )

    query_intent: str | None = Field(
        default=None,
        description="Detected intent of the query",
    )

    key_entities: list[str] = Field(
        default_factory=list,
        description="Key entities extracted from query",
    )

    query_complexity_score: float | None = Field(
        default=None,
        description="Complexity score of the query (0-1)",
    )

    semantic_embeddings_used: bool = Field(
        default=False,
        description="Whether semantic embeddings were used",
    )

    query_expansion_terms: list[str] = Field(
        default_factory=list,
        description="Terms added during query expansion",
    )

    language_detected: str | None = Field(
        default=None,
        description="Detected language of the query",
    )

    query_type: str | None = Field(
        default=None,
        description="Type of query (factual, exploratory, etc.)",
    )

    confidence_score: float | None = Field(
        default=None,
        description="Confidence in query analysis (0-1)",
    )

    processing_time_ms: int | None = Field(
        default=None,
        description="Time taken to analyze query in milliseconds",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
