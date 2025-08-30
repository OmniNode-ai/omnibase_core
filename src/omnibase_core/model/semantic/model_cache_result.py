"""
Cache result model for cached search results.

Provides strongly-typed cache result structure to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelCacheResult(BaseModel):
    """
    A cached search result entry.

    Replaces Dict[str, Any] usage in results_to_cache fields.
    """

    result_id: str = Field(description="Unique identifier for this cache result")

    content: str = Field(description="Result content")

    title: str | None = Field(default=None, description="Result title if available")

    source: str | None = Field(default=None, description="Source path or URL")

    score: float | None = Field(default=None, description="Relevance score")

    rank: int | None = Field(
        default=None,
        description="Rank in original search results",
    )

    timestamp: str | None = Field(
        default=None,
        description="When this result was generated (ISO format)",
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata (string values only)",
    )

    embedding_model: str | None = Field(
        default=None,
        description="Model used for embedding generation",
    )

    retrieval_method: str | None = Field(
        default=None,
        description="Method used to retrieve this result",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
