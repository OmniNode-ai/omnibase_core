"""DateTime-based custom filter model."""

from datetime import datetime

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase


class ModelDateTimeFilter(ModelCustomFilterBase):
    """DateTime-based custom filter."""

    filter_type: str = Field(default="datetime", description="Filter type identifier")
    after: datetime | None = Field(None, description="After this datetime")
    before: datetime | None = Field(None, description="Before this datetime")
    on_date: datetime | None = Field(None, description="On specific date")
    relative_days: int | None = Field(None, description="Within N days from now")
