"""
Retrieval filters model for search operations.

Provides strongly-typed filters to replace Dict[str, Any] usage.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelRetrievalFilters(BaseModel):
    """
    Filters for retrieval operations.

    Replaces Dict[str, Any] usage in filters fields.
    """

    document_types: Optional[List[str]] = Field(
        default=None, description="Filter by document types"
    )

    source_paths: Optional[List[str]] = Field(
        default=None, description="Filter by source file paths"
    )

    tags: Optional[List[str]] = Field(
        default=None, description="Filter by document tags"
    )

    min_score: Optional[float] = Field(
        default=None, description="Minimum similarity score threshold"
    )

    max_results: Optional[int] = Field(
        default=None, description="Maximum number of results to return"
    )

    date_range_start: Optional[str] = Field(
        default=None, description="Start date for document filtering (ISO format)"
    )

    date_range_end: Optional[str] = Field(
        default=None, description="End date for document filtering (ISO format)"
    )

    exclude_sources: Optional[List[str]] = Field(
        default=None, description="Sources to exclude from results"
    )

    require_all_tags: bool = Field(
        default=False, description="Whether all specified tags must be present"
    )

    case_sensitive: bool = Field(
        default=False, description="Whether text matching should be case sensitive"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
