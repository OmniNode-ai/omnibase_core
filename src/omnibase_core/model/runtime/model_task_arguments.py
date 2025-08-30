"""
Task Arguments Models

ONEX-compliant models for task execution arguments with strong typing.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelTaskArguments(BaseModel):
    """Strongly-typed task execution arguments."""

    args: List[str] = Field(
        default_factory=list, description="Positional arguments as strings"
    )
    kwargs: str = Field(default="{}", description="JSON string of keyword arguments")

    @classmethod
    def from_execution_data(
        cls, args: List[str], kwargs_json: str
    ) -> "ModelTaskArguments":
        """Create task arguments from execution data."""
        return cls(args=args, kwargs=kwargs_json)
