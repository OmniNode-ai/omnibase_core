"""
Base class for all custom filters.

Provides common fields and functionality for typed filter models.
"""

from abc import ABC
from typing import Any

from pydantic import BaseModel, Field


class ModelCustomFilterBase(BaseModel, ABC):
    """Base class for all custom filters."""

    filter_type: str = Field(default=..., description="Type of custom filter")
    enabled: bool = Field(default=True, description="Whether filter is active")
    priority: int = Field(
        default=0, description="Filter priority (higher = applied first)"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert filter to dictionary representation."""
        return self.model_dump()
