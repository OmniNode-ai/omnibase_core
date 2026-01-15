"""
Result Dictionary Model.

Clean Pydantic model for Result serialization following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_error_value import ModelErrorValue
from .model_value import ModelValue


class ModelResultDict(BaseModel):
    """
    Clean Pydantic model for Result serialization.

    Represents the dictionary structure when converting Results
    to/from dictionary format with proper type safety.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    success: bool = Field(default=..., description="Whether the operation succeeded")
    value: ModelValue | None = Field(
        default=None,
        description="Success value (if success=True)",
    )
    error: ModelErrorValue | None = Field(
        default=None,
        description="Error value (if success=False)",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations
    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            ModelOnexError: If setting an attribute fails or validation error occurs
                (including pydantic.ValidationError)
        """
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS includes: AttributeError, TypeError,
            # pydantic.ValidationError, ValueError (alphabetically ordered)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            ModelOnexError: If setting an attribute fails or validation error occurs
                (including pydantic.ValidationError)
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS includes: AttributeError, TypeError,
            # pydantic.ValidationError, ValueError (alphabetically ordered)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Configuration failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Type alias for dictionary-based data structures
ModelResultData = dict[str, ModelValue]  # Strongly-typed dict[str, Any] for common data

# Export for use
__all__ = ["ModelResultData", "ModelResultDict"]
