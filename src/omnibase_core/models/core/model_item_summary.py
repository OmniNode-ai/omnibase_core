"""
Item summary model for collection item protocols.

Clean, strongly-typed replacement for collection item dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_item_type import EnumItemType
from omnibase_core.utils.uuid_utilities import uuid_from_string


class ModelItemSummary(BaseModel):
    """
    Clean, strongly-typed model replacing collection item dict return types.

    Eliminates: dict[str, str | int | float | bool | None | list | dict]

    With proper structured data using specific field types.
    """

    # Core item info - UUID-based entity references
    item_id: UUID = Field(
        default_factory=lambda: uuid_from_string("default", "item"),
        description="Unique identifier for the item",
    )
    item_display_name: str = Field(default="", description="Human-readable item name")
    item_type: EnumItemType = Field(
        default=EnumItemType.UNKNOWN,
        description="Type of item",
    )
    description: str = Field(default="", description="Item description")

    # Status and metadata
    is_enabled: bool = Field(default=True, description="Whether item is enabled")
    is_valid: bool = Field(default=True, description="Whether item is valid")
    priority: int = Field(default=0, description="Item priority")

    # Timestamps
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Update timestamp")
    accessed_at: datetime | None = Field(
        default=None, description="Last accessed timestamp"
    )

    # Organization
    tags: list[str] = Field(default_factory=list, description="Item tags")
    categories: list[str] = Field(default_factory=list, description="Item categories")

    # Custom properties with type safety
    string_properties: dict[str, str] = Field(
        default_factory=dict,
        description="String properties",
    )
    numeric_properties: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric properties",
    )
    boolean_properties: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean properties",
    )

    @property
    def name(self) -> str:
        """Get item name with fallback to UUID-based name."""
        return self.item_display_name or f"item_{str(self.item_id)[:8]}"

    def has_properties(self) -> bool:
        """Check if item has custom properties."""
        return bool(
            self.string_properties
            or self.numeric_properties
            or self.boolean_properties,
        )


# Export the model
__all__ = ["ModelItemSummary"]
