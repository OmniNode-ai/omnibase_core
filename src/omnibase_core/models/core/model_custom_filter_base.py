"""
Base class for all custom filters.

Provides common fields and functionality for typed filter models.
"""

from abc import ABC

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelCustomFilterBase(BaseModel, ABC):
    """Base class for all custom filters."""

    filter_type: str = Field(default=..., description="Type of custom filter")
    enabled: bool = Field(default=True, description="Whether filter is active")
    priority: int = Field(
        default=0, description="Filter priority (higher = applied first)"
    )

    def to_dict(self) -> SerializedDict:
        """Convert filter to dictionary representation."""
        return self.model_dump()
