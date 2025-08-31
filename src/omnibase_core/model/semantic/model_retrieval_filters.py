"""
Retrieval filters model for search operations.

Provides strongly-typed filters to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelRetrievalFilters(BaseModel):
    """
    Filters for retrieval operations.

    Replaces Dict[str, Any] usage in filters fields.
    """

    document_types: list[str] | None = Field(
        default=None,
        description="Filter by document types",
    )

    source_paths: list[str] | None = Field(
        default=None,
        description="Filter by source file paths",
    )

    tags: list[str] | None = Field(
        default=None,
        description="Filter by document tags",
    )

    min_score: float | None = Field(
        default=None,
        description="Minimum similarity score threshold",
    )

    max_results: int | None = Field(
        default=None,
        description="Maximum number of results to return",
    )

    date_range_start: str | None = Field(
        default=None,
        description="Start date for document filtering (ISO format)",
    )

    date_range_end: str | None = Field(
        default=None,
        description="End date for document filtering (ISO format)",
    )

    exclude_sources: list[str] | None = Field(
        default=None,
        description="Sources to exclude from results",
    )

    require_all_tags: bool = Field(
        default=False,
        description="Whether all specified tags must be present",
    )

    case_sensitive: bool = Field(
        default=False,
        description="Whether text matching should be case sensitive",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
