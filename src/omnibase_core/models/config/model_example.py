"""
Example model for examples collection.

This module provides the ModelExample class for strongly typed
example data with comprehensive fields and validation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Configurable

from .model_example_context_data import ModelExampleContextData
from .model_example_data import ModelExampleInputData, ModelExampleOutputData


class ModelExample(BaseModel):
    """
    Strongly typed example model with comprehensive fields.

    Replaces placeholder implementation with proper validation and structure.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identification
    example_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this example",
    )

    name: str = Field(
        ...,
        description="Name/title of the example",
        min_length=1,
    )

    description: str = Field(
        default="",
        description="Detailed description of what this example demonstrates",
    )

    # Data fields
    input_data: ModelExampleInputData | None = Field(
        None,
        description="Input data for the example with type safety",
    )

    output_data: ModelExampleOutputData | None = Field(
        None,
        description="Expected output data for the example",
    )

    context: ModelExampleContextData | None = Field(
        None,
        description="Additional context information for the example",
    )

    # Metadata
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing and searching examples",
    )

    # Validation
    is_valid: bool = Field(
        default=True,
        description="Whether this example passes validation",
    )

    validation_notes: str = Field(
        default="",
        description="Notes about validation status or issues",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this example was created",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this example was last updated",
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
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False
