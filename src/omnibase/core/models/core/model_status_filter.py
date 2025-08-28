"""Status-based custom filter model."""

from typing import List

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase


class ModelStatusFilter(ModelCustomFilterBase):
    """Status-based custom filter."""

    filter_type: str = Field(default="status", description="Filter type identifier")
    allowed_statuses: List[str] = Field(..., description="Allowed status values")
    blocked_statuses: List[str] = Field(
        default_factory=list, description="Blocked status values"
    )
    include_unknown: bool = Field(
        False, description="Include items with unknown status"
    )
