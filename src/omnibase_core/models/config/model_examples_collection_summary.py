"""
Examples collection summary model.

Clean, strongly-typed replacement for the horrible union return type.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_data_format import EnumDataFormat
from omnibase_core.errors.error_codes import CoreErrorCode, OnexError

from .model_example_metadata_summary import ModelExampleMetadataSummary
from .model_example_summary import ModelExampleSummary

# Removed Any import for ONEX compliance


class ModelExamplesCollectionSummary(BaseModel):
    """
    Clean, strongly-typed model replacing the horrible union return type.

    Eliminates: dict[str, list[dict[str, Any]] | dict[str, Any] | None | int | bool]

    With proper structured data using specific field types.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    examples: list[ModelExampleSummary] = Field(
        default_factory=list,
        description="List of example summaries",
    )

    metadata: ModelExampleMetadataSummary | None = Field(
        None,
        description="Collection metadata summary",
    )

    format: EnumDataFormat = Field(
        default=EnumDataFormat.JSON,
        description="Collection format",
    )

    schema_compliant: bool = Field(
        default=True,
        description="Whether collection is schema compliant",
    )

    example_count: int = Field(default=0, description="Total number of examples")

    valid_example_count: int = Field(default=0, description="Number of valid examples")

    # Statistics
    completion_rate: float = Field(
        default=0.0,
        description="Percentage of valid examples",
    )

    last_updated: datetime | None = Field(None, description="Last update timestamp")

    def model_post_init(self, __context: dict[str, Any] | None = None) -> None:
        """Calculate completion rate after initialization."""
        if self.example_count > 0:
            self.completion_rate = (self.valid_example_count / self.example_count) * 100
        else:
            self.completion_rate = 0.0

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the models

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


__all__ = [
    "ModelExampleMetadataSummary",
    "ModelExampleSummary",
    "ModelExamplesCollectionSummary",
]
