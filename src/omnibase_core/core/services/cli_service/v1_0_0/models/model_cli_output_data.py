"""
CLI output data model for ONEX CLI operations.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelCliOutputData(BaseModel):
    """Strongly typed CLI output data."""

    content: str = Field(default="")
    format_type: str = Field(default="text")
    success: bool = Field(default=True)
