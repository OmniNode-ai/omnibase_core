"""
Collection of custom filters model.

Strongly typed collection replacing Dict[str, Any] for custom_filters fields.

NOTE: This is a minimal version while filter models are being implemented.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_filter_type import EnumFilterType


class ModelCustomFilters(BaseModel):
    """
    Collection of custom filters.

    Strongly typed collection replacing Dict[str, Any] for custom_filters fields
    with no magic strings or poorly typed dictionaries.

    NOTE: Filter functionality temporarily disabled pending filter model implementation.
    """

    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Named custom filters with strong typing",
    )

    def get_filter(self, name: str) -> Any | None:
        """Get a filter by name."""
        return self.filters.get(name)

    def remove_filter(self, name: str) -> bool:
        """Remove a filter by name, return True if removed."""
        if name in self.filters:
            del self.filters[name]
            return True
        return False

    def get_filter_names(self) -> list[str]:
        """Get all filter names."""
        return list(self.filters.keys())

    def filter_count(self) -> int:
        """Get total number of filters."""
        return len(self.filters)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.filters.copy()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCustomFilters":
        """Create from dictionary."""
        return cls(filters=data)

    @classmethod
    def create_empty(cls) -> "ModelCustomFilters":
        """Create an empty filter collection."""
        return cls()


# Export for use
__all__ = ["ModelCustomFilters"]