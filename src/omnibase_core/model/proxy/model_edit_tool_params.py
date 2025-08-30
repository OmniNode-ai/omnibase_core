"""Strongly typed model for Edit tool parameters."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from omnibase_core.model.proxy.model_tool_parameter_base import \
    ModelToolParameterBase


class ModelEditToolParams(ModelToolParameterBase):
    """Parameters for Edit tool with strong typing."""

    file_path: Path = Field(..., description="Absolute path to file to edit")
    old_string: str = Field(..., description="Text to replace", min_length=0)
    new_string: str = Field(..., description="Replacement text", min_length=0)
    replace_all: bool = Field(False, description="Replace all occurrences")

    @field_validator("file_path")
    @classmethod
    def validate_absolute_path(cls, v: Path) -> Path:
        """Ensure path is absolute."""
        if not v.is_absolute():
            raise ValueError(f"Path must be absolute, got: {v}")
        return v

    @field_validator("old_string", "new_string")
    @classmethod
    def validate_different_strings(cls, v: str, info) -> str:
        """Ensure old and new strings are different."""
        if info.field_name == "new_string" and "old_string" in info.data:
            if v == info.data["old_string"]:
                raise ValueError("new_string must be different from old_string")
        return v
