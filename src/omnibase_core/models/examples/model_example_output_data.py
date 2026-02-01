"""
Example output data model.

This module provides the ModelExampleOutputData class for clean,
strongly-typed replacement for dict[str, Any] in example output data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_cli_status import EnumCliStatus
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_data_type import EnumDataType
from omnibase_core.enums.enum_io_type import EnumIoType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelExampleOutputData(BaseModel):
    """
    Clean model for example output data.

    Replaces dict[str, Any] with structured data model.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core data fields
    data_type: EnumIoType = Field(
        default=EnumIoType.OUTPUT,
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
        default=None,
        description="Processing time in milliseconds",
    )
    memory_usage_mb: float | None = Field(
        default=None, description="Memory usage in MB"
    )

    # Validation info
    is_expected: bool = Field(
        default=True,
        description="Whether output matches expectations",
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
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelExampleOutputData"]
