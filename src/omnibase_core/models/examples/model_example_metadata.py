"""
Example metadata model for examples collection.

This module provides the ModelExampleMetadata class for metadata
about example collections with enhanced structure.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_difficulty_level import EnumDifficultyLevel
from omnibase_core.enums.enum_example_category import EnumExampleCategory
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelExampleMetadata(BaseModel):
    """
    Metadata for example collections with enhanced structure.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    title: str = Field(
        default="",
        description="Title for the examples collection",
    )

    description: str | None = Field(
        default=None,
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
        default=None,
        description="Category this collection belongs to",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS covers: AttributeError, TypeError, ValidationError, ValueError
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        This base implementation always returns True. Subclasses should override
        this method to perform custom validation and catch specific exceptions
        (e.g., ValidationError, ValueError) when implementing validation logic.
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True
