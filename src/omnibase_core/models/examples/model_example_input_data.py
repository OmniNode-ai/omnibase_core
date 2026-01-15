"""
Example input data model.

This module provides the ModelExampleInputData class for clean,
strongly-typed replacement for dict[str, Any] in example input data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_data_type import EnumDataType
from omnibase_core.enums.enum_io_type import EnumIoType
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelExampleInputData(BaseModel):
    """
    Clean model for example input data.

    Replaces dict[str, Any] with structured data model.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core data fields
    data_type: EnumIoType = Field(
        default=EnumIoType.INPUT,
        description="Type of input data",
    )
    format: EnumDataType = Field(default=EnumDataType.JSON, description="Data format")

    # Input parameters using strongly-typed metadata values
    parameters: dict[str, ModelMetadataValue] = Field(
        default_factory=dict,
        description="Input parameters with type-safe values",
    )

    # Configuration settings using string values for simplicity
    configuration: dict[str, str] = Field(
        default_factory=dict,
        description="Configuration settings for the input (string values)",
    )

    # Validation info
    schema_version: ModelSemVer | None = Field(
        default=None,
        description="Schema version for validation",
    )
    is_validated: bool = Field(default=False, description="Whether input is validated")

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
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


__all__ = ["ModelExampleInputData"]
