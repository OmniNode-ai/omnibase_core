"""
Change Item Model

Individual change detection result.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelChangeItem(BaseModel):
    """Individual change detection result."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    path: str = Field(description="File path that changed")
    last_modified: datetime = Field(description="When the file was last modified")
    change_type: str = Field(description="Type of change (added, modified, deleted)")
    size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="File size in bytes",
    )
