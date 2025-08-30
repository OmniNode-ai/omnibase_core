"""Strongly typed model for Read tool parameters."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from omnibase_core.model.proxy.model_tool_parameter_base import \
    ModelToolParameterBase


class ModelReadToolParams(ModelToolParameterBase):
    """Parameters for Read tool with strong typing."""

    file_path: Path = Field(..., description="Absolute path to file to read")
    limit: Optional[int] = Field(
        None, description="Number of lines to read", ge=1, le=10000
    )
    offset: Optional[int] = Field(None, description="Starting line number", ge=0)

    @field_validator("file_path")
    @classmethod
    def validate_absolute_path(cls, v: Path) -> Path:
        """Ensure path is absolute."""
        if not v.is_absolute():
            raise ValueError(f"Path must be absolute, got: {v}")
        return v
