from __future__ import annotations

import uuid
from typing import Dict, Generic

from pydantic import Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Generic collection summary model.

Strongly-typed summary for generic collections that replaces Dict[str, Any]
anti-pattern with proper type safety.
"""


from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode


class ModelGenericCollectionSummary(BaseModel):
    """
    Strongly-typed summary for generic collections.

    Replaces Dict[str, Any] anti-pattern with proper type safety.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    collection_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the collection",
    )
    collection_display_name: str = Field(
        default="",
        description="Human-readable display name for the collection",
    )
    total_items: int = Field(description="Total number of items in collection")
    enabled_items: int = Field(description="Number of enabled items")
    valid_items: int = Field(description="Number of valid items")
    created_at: datetime = Field(description="When the collection was created")
    updated_at: datetime = Field(description="When the collection was last modified")
    has_items: bool = Field(description="Whether the collection contains any items")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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


# Export for use
__all__ = ["ModelGenericCollectionSummary"]
