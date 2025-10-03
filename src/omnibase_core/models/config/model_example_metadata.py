"""
Example metadata model for examples collection.

This module provides the ModelExampleMetadata class for metadata
about example collections with enhanced structure.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_difficulty_level import EnumDifficultyLevel
from omnibase_core.enums.enum_example_category import EnumExampleCategory
from omnibase_core.errors.error_codes import CoreErrorCode, OnexError


class ModelExampleMetadata(BaseModel):
    """
    Metadata for example collections with enhanced structure.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    title: str = Field(
        default="",
        description="Title for the examples collection",
    )

    description: str | None = Field(
        None,
        description="Description of the examples collection",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for the entire collection",
    )

    difficulty: EnumDifficultyLevel = Field(
        default=EnumDifficultyLevel.BEGINNER,
        description="Difficulty level for the examples collection",
    )

    category: EnumExampleCategory | None = Field(
        None,
        description="Category this collection belongs to",
    )

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
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e
