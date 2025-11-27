"""Status-based custom filter model."""

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase


class ModelStatusFilter(ModelCustomFilterBase):
    """Status-based custom filter."""

    filter_type: str = Field(default="status", description="Filter type identifier")
    allowed_statuses: list[str] = Field(
        default=..., description="Allowed status values"
    )
    blocked_statuses: list[str] = Field(
        default_factory=list,
        description="Blocked status values",
    )
    include_unknown: bool = Field(
        default=False,
        description="Include items with unknown status",
    )
