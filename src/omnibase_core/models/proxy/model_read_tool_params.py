"""Strongly typed model for Read tool parameters."""

from pathlib import Path

from pydantic import Field, field_validator

from omnibase_core.models.proxy.model_tool_parameter_base import ModelToolParameterBase


class ModelReadToolParams(ModelToolParameterBase):
    """Parameters for Read tool with strong typing."""

    file_path: Path = Field(..., description="Absolute path to file to read")
    limit: int | None = Field(
        None,
        description="Number of lines to read",
        ge=1,
        le=10000,
    )
    offset: int | None = Field(None, description="Starting line number", ge=0)

    @field_validator("file_path")
    @classmethod
    def validate_absolute_path(cls, v: Path) -> Path:
        """Ensure path is absolute."""
        if not v.is_absolute():
            msg = f"Path must be absolute, got: {v}"
            raise ValueError(msg)
        return v
