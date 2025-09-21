"""
Item summary model for collection item protocols.

Clean, strongly-typed replacement for collection item dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_item_type import EnumItemType
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
    item_type: EnumItemType = Field(
        default=EnumItemType.UNKNOWN, description="Type of item"
    )
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
            self.string_properties or self.numeric_properties or self.boolean_properties
        )

    @classmethod
    def create_from_dict(
        cls,
        data: dict[
            str,
            str
            | int
            | float
            | bool
            | None
            | list[Any]
            | dict[str, str | int | float | bool | None],
        ],
    ) -> "ModelItemSummary":
        """Create item summary from legacy dict for backward compatibility."""
        # Extract known fields
        item_id = uuid_from_string(str(data.get("name", "default")), "item")
        item_display_name = str(data.get("name")) if data.get("name") else None
        # Convert string to enum, fallback to UNKNOWN if not valid
        item_type_str = str(data.get("type", "unknown"))
        try:
            item_type = EnumItemType(item_type_str)
        except ValueError:
            item_type = EnumItemType.UNKNOWN
        description = str(data.get("description")) if data.get("description") else None
        is_enabled = bool(data.get("enabled", True))
        is_valid = bool(data.get("valid", True))
        priority_raw = data.get("priority", 0)
        priority = (
            int(priority_raw)
            if isinstance(priority_raw, (int, float, str)) and priority_raw
            else 0
        )

        # Extract tags and categories with type safety
        tags: list[str] = []
        categories: list[str] = []
        tags_raw = data.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(tag) for tag in tags_raw if tag is not None]
        categories_raw = data.get("categories")
        if isinstance(categories_raw, list):
            categories = [str(cat) for cat in categories_raw if cat is not None]

        # Process custom properties by type
        string_props: dict[str, str] = {}
        numeric_props: dict[str, float] = {}
        boolean_props: dict[str, bool] = {}

        # Known fields to skip
        known_fields = {
            "name",
            "type",
            "description",
            "enabled",
            "valid",
            "priority",
            "tags",
            "categories",
            "created_at",
            "updated_at",
            "accessed_at",
        }

        for key, value in data.items():
            if key in known_fields or value is None:
                continue

            if isinstance(value, str):
                string_props[key] = value
            elif isinstance(value, bool):
                boolean_props[key] = value
            elif isinstance(value, (int, float)):
                numeric_props[key] = float(value)
            elif isinstance(value, (list, dict)):
                # Convert complex types to string representation
                string_props[key] = str(value)

        # Extract timestamps with type safety
        created_at = None
        updated_at = None
        accessed_at = None

        if "created_at" in data and data["created_at"]:
            try:
                created_at = datetime.fromisoformat(str(data["created_at"]))
            except (ValueError, TypeError):
                created_at = None

        if "updated_at" in data and data["updated_at"]:
            try:
                updated_at = datetime.fromisoformat(str(data["updated_at"]))
            except (ValueError, TypeError):
                updated_at = None

        if "accessed_at" in data and data["accessed_at"]:
            try:
                accessed_at = datetime.fromisoformat(str(data["accessed_at"]))
            except (ValueError, TypeError):
                accessed_at = None

        return cls(
            item_id=item_id,
            item_display_name=item_display_name,
            item_type=item_type,
            description=description,
            is_enabled=is_enabled,
            is_valid=is_valid,
            priority=priority,
            created_at=created_at,
            updated_at=updated_at,
            accessed_at=accessed_at,
            tags=tags,
            categories=categories,
            string_properties=string_props,
            numeric_properties=numeric_props,
            boolean_properties=boolean_props,
        )


# Export the model
__all__ = ["ModelItemSummary"]
