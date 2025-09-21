"""
Item summary model for collection item protocols.

Clean, strongly-typed replacement for collection item dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ...utils.uuid_utilities import uuid_from_string


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
    item_display_name: str | None = Field(None, description="Human-readable item name")
    item_type: str = Field(default="unknown", description="Type of item")
    description: str | None = Field(None, description="Item description")

    # Status and metadata
    is_enabled: bool = Field(default=True, description="Whether item is enabled")
    is_valid: bool = Field(default=True, description="Whether item is valid")
    priority: int = Field(default=0, description="Item priority")

    # Timestamps
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Update timestamp")
    accessed_at: datetime | None = Field(None, description="Last accessed timestamp")

    # Organization
    tags: list[str] = Field(default_factory=list, description="Item tags")
    categories: list[str] = Field(default_factory=list, description="Item categories")

    # Custom properties with type safety
    string_properties: dict[str, str] = Field(
        default_factory=dict, description="String properties"
    )
    numeric_properties: dict[str, float] = Field(
        default_factory=dict, description="Numeric properties"
    )
    boolean_properties: dict[str, bool] = Field(
        default_factory=dict, description="Boolean properties"
    )

    @property
    def name(self) -> str:
        """Get item name with fallback to UUID-based name."""
        return self.item_display_name or f"item_{str(self.item_id)[:8]}"

    @name.setter
    def name(self, value: str) -> None:
        """Set item name (for backward compatibility)."""
        self.item_display_name = value
        self.item_id = uuid_from_string(value, "item")

    def has_properties(self) -> bool:
        """Check if item has custom properties."""
        return bool(
            self.string_properties
            or self.numeric_properties
            or self.boolean_properties
        )

    @classmethod
    def create_from_dict(
        cls,
        data: dict[str, str | int | float | bool | None | list | dict],
    ) -> "ModelItemSummary":
        """Create item summary from legacy dict for backward compatibility."""
        # Extract known fields
        item_id = uuid_from_string(str(data.get("name", "default")), "item")
        item_display_name = str(data.get("name")) if data.get("name") else None
        item_type = str(data.get("type", "unknown"))
        description = str(data.get("description")) if data.get("description") else None
        is_enabled = bool(data.get("enabled", True))
        is_valid = bool(data.get("valid", True))
        priority = int(data.get("priority", 0)) if data.get("priority") else 0

        # Extract tags and categories
        tags = []
        categories = []
        if isinstance(data.get("tags"), list):
            tags = [str(tag) for tag in data["tags"]]
        if isinstance(data.get("categories"), list):
            categories = [str(cat) for cat in data["categories"]]

        # Process custom properties by type
        string_props = {}
        numeric_props = {}
        boolean_props = {}

        # Known fields to skip
        known_fields = {
            "name", "type", "description", "enabled", "valid", "priority",
            "tags", "categories", "created_at", "updated_at", "accessed_at"
        }

        for key, value in data.items():
            if key in known_fields or value is None:
                continue

            if isinstance(value, str):
                string_props[key] = value
            elif isinstance(value, (int, float)):
                numeric_props[key] = float(value)
            elif isinstance(value, bool):
                boolean_props[key] = value
            elif isinstance(value, (list, dict)):
                # Convert complex types to string representation
                string_props[key] = str(value)

        return cls(
            item_id=item_id,
            item_display_name=item_display_name,
            item_type=item_type,
            description=description,
            is_enabled=is_enabled,
            is_valid=is_valid,
            priority=priority,
            tags=tags,
            categories=categories,
            string_properties=string_props,
            numeric_properties=numeric_props,
            boolean_properties=boolean_props,
        )


# Export the model
__all__ = ["ModelItemSummary"]