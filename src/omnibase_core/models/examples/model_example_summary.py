"""
Example summary model.

This module provides the ModelExampleSummary class for clean
individual example summary data following ONEX naming conventions.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_example_data import ModelExampleInputData, ModelExampleOutputData


class ModelExampleSummary(BaseModel):
    """Clean model for individual example summary data.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    example_id: UUID = Field(default_factory=uuid4, description="Example identifier")

    # Entity reference - UUID-based with display name
    entity_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the example entity",
    )
    display_name: str = Field(default=..., description="Example display name")

    description: str | None = Field(default=None, description="Example description")
    is_valid: bool = Field(default=True, description="Whether example is valid")
    input_data: ModelExampleInputData | None = Field(
        default=None, description="Input data"
    )
    output_data: ModelExampleOutputData | None = Field(
        default=None, description="Output data"
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
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Returns True for well-constructed instances. Override in subclasses
        for custom validation logic.
        """
        # Basic validation - Pydantic handles field constraints
        # Override in specific models for custom validation
        return True


__all__ = ["ModelExampleSummary"]
