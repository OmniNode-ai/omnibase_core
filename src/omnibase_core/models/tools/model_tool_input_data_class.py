"""ModelToolInputData Class.

Input data for tool execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class ModelToolInputData(BaseModel):
    """Input data for tool execution."""

    operation: str = Field(..., description="Operation to perform")
    source_path: str | None = Field(
        None,
        description="Source file or directory path",
    )
    target_path: str | None = Field(
        None,
        description="Target file or directory path",
    )
    config: dict[str, str | int | float | bool] | None = Field(
        None,
        description="Configuration parameters",
    )
    metadata: dict[str, str | int | float | bool] | None = Field(
        None,
        description="Metadata for the operation",
    )
    options: list[str] | None = Field(None, description="Additional options")
