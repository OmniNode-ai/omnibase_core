"""
CLI tool input state model for ONEX CLI operations.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelCliToolInputState(BaseModel):
    """Strongly typed tool input state."""

    action: str = Field(...)
    parameters: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)
