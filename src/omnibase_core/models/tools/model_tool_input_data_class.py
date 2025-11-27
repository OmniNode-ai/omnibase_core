"""ModelToolInputData Class.

Input data for tool execution.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelToolInputData(BaseModel):
    """Input data for tool execution."""

    operation: str = Field(default=..., description="Operation to perform")
    source_path: str | None = Field(
        default=None,
        description="Source file or directory path",
    )
    target_path: str | None = Field(
        default=None,
        description="Target file or directory path",
    )
    config: dict[str, str | int | float | bool] | None = Field(
        default=None,
        description="Configuration parameters",
    )
    metadata: dict[str, str | int | float | bool] | None = Field(
        default=None,
        description="Metadata for the operation",
    )
    options: list[str] | None = Field(default=None, description="Additional options")
