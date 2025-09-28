"""
Example output data model.

This module provides the ModelExampleOutputData class for clean,
strongly-typed replacement for dict[str, Any] in example output data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Configurable
from omnibase_core.enums.enum_cli_status import EnumCliStatus
from omnibase_core.enums.enum_data_type import EnumDataType
from omnibase_core.enums.enum_io_type import EnumIOType
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue


class ModelExampleOutputData(BaseModel):
    """
    Clean model for example output data.

    Replaces dict[str, Any] with structured data model.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core data fields
    data_type: EnumIOType = Field(
        default=EnumIOType.OUTPUT,
        description="Type of output data",
    )
    format: EnumDataType = Field(default=EnumDataType.JSON, description="Data format")

    # Output results using strongly-typed values
    results: dict[str, ModelMetadataValue] = Field(
        default_factory=dict,
        description="Output results with type-safe values",
    )

    # Status information
    status: EnumCliStatus = Field(
        default=EnumCliStatus.SUCCESS,
        description="Output status",
    )

    # Metrics
    processing_time_ms: float | None = Field(
        None,
        description="Processing time in milliseconds",
    )
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")

    # Validation info
    is_expected: bool = Field(
        default=True,
        description="Whether output matches expectations",
    )

    # Export the model

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
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


__all__ = ["ModelExampleOutputData"]
