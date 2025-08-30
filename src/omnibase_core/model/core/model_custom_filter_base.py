"""
Base class for all custom filters.

Provides common fields and functionality for typed filter models.
"""

from abc import ABC
from typing import Any, Dict

from pydantic import BaseModel, Field


class ModelCustomFilterBase(BaseModel, ABC):
    """Base class for all custom filters."""

    filter_type: str = Field(..., description="Type of custom filter")
    enabled: bool = Field(True, description="Whether filter is active")
    priority: int = Field(0, description="Filter priority (higher = applied first)")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return self.model_dump(exclude_none=True)
