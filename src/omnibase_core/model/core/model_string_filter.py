"""String-based custom filter model."""

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase


class ModelStringFilter(ModelCustomFilterBase):
    """String-based custom filter."""

    filter_type: str = Field(default="string", description="Filter type identifier")
    pattern: str = Field(..., description="String pattern to match")
    case_sensitive: bool = Field(False, description="Case sensitive matching")
    regex: bool = Field(False, description="Use regex matching")
    contains: bool = Field(True, description="Match if contains (vs exact match)")
