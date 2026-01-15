"""
Generic container pattern for single-value models with metadata.

This module provides a reusable generic container that can replace
specialized single-value containers across the codebase, reducing
repetitive patterns while maintaining type safety.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import Field

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelContainer[T](BaseModel):
    """
    Generic container for single values with metadata and validation.

    This pattern can replace specialized single-value containers like
    ModelNumericValue, ModelValidationValue, etc. when the specialized
    behavior isn't needed.

    Type Parameters:
        T: The type of value stored in the container
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    value: T = Field(description="The contained value")

    container_type: str = Field(
        description="Type identifier for the container",
    )

    source: str | None = Field(
        default=None,
        description="Source of the contained value",
    )

    is_validated: bool = Field(
        default=False,
        description="Whether value has been validated",
    )

    validation_notes: str | None = Field(
        default=None,
        description="Notes about validation status",
    )

    @classmethod
    def create(
        cls,
        value: T,
        container_type: str,
        source: str | None = None,
        is_validated: bool = False,
        validation_notes: str | None = None,
    ) -> ModelContainer[T]:
        """
        Create a new container with the specified value and metadata.

        Args:
            value: The value to contain
            container_type: Type identifier for the container
            source: Optional source of the value
            is_validated: Whether the value has been validated
            validation_notes: Optional validation notes

        Returns:
            New container instance
        """
        return cls(
            value=value,
            container_type=container_type,
            source=source,
            is_validated=is_validated,
            validation_notes=validation_notes,
        )

    @classmethod
    def create_validated(
        cls,
        value: T,
        container_type: str,
        source: str | None = None,
        validation_notes: str | None = None,
    ) -> ModelContainer[T]:
        """
        Create a validated container.

        Args:
            value: The value to contain
            container_type: Type identifier for the container
            source: Optional source of the value
            validation_notes: Optional validation notes

        Returns:
            New validated container instance
        """
        return cls.create(
            value=value,
            container_type=container_type,
            source=source,
            is_validated=True,
            validation_notes=validation_notes,
        )

    def get_value(self) -> T:
        """Get the contained value."""
        return self.value

    def update_value(
        self,
        new_value: T,
        validation_notes: str | None = None,
        mark_validated: bool = False,
    ) -> None:
        """
        Update the contained value.

        Args:
            new_value: New value to store
            validation_notes: Optional validation notes
            mark_validated: Whether to mark as validated
        """
        self.value = new_value
        if validation_notes is not None:
            self.validation_notes = validation_notes
        if mark_validated:
            self.is_validated = True

    def map_value(self, mapper: Callable[[T], T]) -> ModelContainer[T]:
        """
        Transform the contained value using a mapper function.

        Args:
            mapper: Function to transform the value

        Returns:
            New container with transformed value

        Raises:
            ModelOnexError: If the mapper function fails for any reason
        """
        try:
            new_value = mapper(self.value)
            return ModelContainer.create(
                value=new_value,
                container_type=self.container_type,
                source=self.source,
                is_validated=False,  # Reset validation after transformation
                validation_notes="Value transformed, requires re-validation",
            )
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Failed to map container value: {e!s}",
                details=ModelErrorContext.with_context(
                    {
                        "container_type": ModelSchemaValue.from_value(
                            self.container_type,
                        ),
                        "original_value": ModelSchemaValue.from_value(str(self.value)),
                        "error": ModelSchemaValue.from_value(str(e)),
                    },
                ),
            ) from e

    def validate_with(
        self,
        validator: Callable[[T], bool],
        error_message: str = "Validation failed",
    ) -> bool:
        """
        Validate the contained value using a validator function.

        Args:
            validator: Function that returns True if value is valid
            error_message: Error message if validation fails

        Returns:
            True if validation passes

        Raises:
            ModelOnexError: If validation fails
        """
        try:
            is_valid = validator(self.value)
            if is_valid:
                self.is_validated = True
                self.validation_notes = "Validation passed"
                return True
            self.is_validated = False
            self.validation_notes = error_message
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=error_message,
                details=ModelErrorContext.with_context(
                    {
                        "container_type": ModelSchemaValue.from_value(
                            self.container_type,
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    },
                ),
            )
        except (AttributeError, ModelOnexError, TypeError, ValueError) as e:
            if isinstance(e, ModelOnexError):
                raise
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Validation error: {e!s}",
                details=ModelErrorContext.with_context(
                    {
                        "container_type": ModelSchemaValue.from_value(
                            self.container_type,
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                        "error": ModelSchemaValue.from_value(str(e)),
                    },
                ),
            ) from e

    def compare_value(self, other: object) -> bool:
        """
        Compare the contained value with another value or container.

        Uses strict type comparison to ensure type safety and ONEX compliance.

        Args:
            other: Value or container to compare with

        Returns:
            True if values are equal and of the same type
        """
        if isinstance(other, ModelContainer):
            # Compare both value and type for strict equality
            return self.value == other.value and type(self.value) is type(other.value)
        # Compare both value and type for strict equality
        return self.value == other and type(self.value) is type(other)

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison based on contained value with strict type checking.

        Uses strict type comparison to ensure type safety and ONEX compliance.
        """
        if isinstance(other, ModelContainer):
            # Compare both value and type for strict equality
            return self.value == other.value and type(self.value) is type(other.value)
        # Compare both value and type for strict equality
        return self.value == other and type(self.value) is type(other)

    def __str__(self) -> str:
        """String representation."""
        status = "validated" if self.is_validated else "unvalidated"
        source_info = f" from {self.source}" if self.source else ""
        return f"{self.container_type}({self.value}) [{status}]{source_info}"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            "ModelContainer("
            f"value={self.value!r}, "
            f"container_type={self.container_type!r}, "
            f"source={self.source!r}, "
            f"is_validated={self.is_validated}"
            ")"
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Note: Previously had factory functions (string_container, int_container, etc.)
    # These were removed to comply with ONEX strong typing standards.
    # Use explicit creation: ModelContainer.create(value, container_type, ...)

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
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
        except (AttributeError, KeyError, TypeError, ValueError) as e:
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
__all__ = [
    "ModelContainer",
]
