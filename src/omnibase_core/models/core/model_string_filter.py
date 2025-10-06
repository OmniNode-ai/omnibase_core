"""String-based custom filter model."""

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase


class ModelStringFilter(ModelCustomFilterBase):
    """String-based custom filter."""

    filter_type: str = Field(default="string", description="Filter type identifier")
    pattern: str = Field(default=..., description="String pattern to match")
    case_sensitive: bool = Field(default=False, description="Case sensitive matching")
    regex: bool = Field(default=False, description="Use regex matching")
    contains: bool = Field(
        default=True, description="Match if contains (vs exact match)"
    )
