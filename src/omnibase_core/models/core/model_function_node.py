"""
Function Node Model for metadata node collections.

Represents a function node with typed fields for metadata collections.
"""

from typing import Any
from pydantic import BaseModel, Field


class ModelFunctionNode(BaseModel):
    """
    Function node representation for metadata collections.

    Provides structured fields for function nodes used in metadata
    node collections and workflow processing.
    """

    # Function identification
    name: str = Field(..., description="Function name")
    description: str = Field("", description="Function description")
    version: str = Field("1.0.0", description="Function version")

    # Function metadata
    category: str = Field("general", description="Function category")
    tags: list[str] = Field(default_factory=list, description="Function tags")

    # Function parameters
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Function parameters"
    )

    # Function execution info
    async_execution: bool = Field(False, description="Whether function is async")
    timeout_seconds: int | None = Field(None, description="Execution timeout")

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional function metadata"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelFunctionNode":
        """Create from dictionary representation."""
        return cls(**data)