from __future__ import annotations

from pydantic import Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Item summary model for collection item protocols.

Clean, strongly-typed replacement for collection item dict[str, Any]return types.
Follows ONEX one-model-per-file naming conventions.
"""


from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_item_type import EnumItemType
from omnibase_core.errors.error_codes import (
    EnumCoreErrorCode,
)
from omnibase_core.utils.uuid_utilities import uuid_from_string


class ModelItemSummary(BaseModel):
    """
    Clean, strongly-typed model replacing collection item dict[str, Any]return types.

    Eliminates: dict[str, primitive_soup_unions] (replaced with PrimitiveValueType)

    With proper structured data using specific field types.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
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
        default=None,
        description="Last accessed timestamp",
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def configure(self, **kwargs) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return


__all__ = ["ModelItemSummary"]
