"""
CLI error details model for ONEX CLI operations.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelCliErrorDetails(BaseModel):
    """Strongly typed error details."""

    error_code: str = Field(...)
    error_message: str = Field(...)
    context: dict[str, str] = Field(default_factory=dict)
