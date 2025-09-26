"""
Generic container pattern for single-value models with metadata.

This module provides a reusable generic container that can replace
specialized single-value containers across the codebase, reducing
repetitive patterns while maintaining type safety.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar, cast

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Type variable for contained value
T = TypeVar("T")


class ModelContainer(BaseModel, Generic[T]):
    """
    Generic container for single values with metadata and validation.

    This pattern can replace specialized single-value containers like
    ModelNumericValue, ModelValidationValue, etc. when the specialized
    behavior isn't needed.

    Type Parameters:
        T: The type of value stored in the container
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
        except Exception as e:
            raise OnexError(
                code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Failed to map container value: {e!s}",
                details=ModelErrorContext.with_context(
                    {
                        "container_type": ModelSchemaValue.from_value(
                            self.container_type
                        ),
                        "original_value": ModelSchemaValue.from_value(str(self.value)),
                        "error": ModelSchemaValue.from_value(str(e)),
                    }
                ),
            )

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
            OnexError: If validation fails
        """
        try:
            is_valid = validator(self.value)
            if is_valid:
                self.is_validated = True
                self.validation_notes = "Validation passed"
                return True
            self.is_validated = False
            self.validation_notes = error_message
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=error_message,
                details=ModelErrorContext.with_context(
                    {
                        "container_type": ModelSchemaValue.from_value(
                            self.container_type
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    }
                ),
            )
        except Exception as e:
            if isinstance(e, OnexError):
                raise
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Validation error: {e!s}",
                details=ModelErrorContext.with_context(
                    {
                        "container_type": ModelSchemaValue.from_value(
                            self.container_type
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                        "error": ModelSchemaValue.from_value(str(e)),
                    }
                ),
            )

    def compare_value(self, other: object) -> bool:
        """
        Compare the contained value with another value or container.

        Args:
            other: Value or container to compare with

        Returns:
            True if values are equal
        """
        if isinstance(other, ModelContainer):
            return bool(self.value == other.value)
        return bool(self.value == other)

    def __eq__(self, other: object) -> bool:
        """Equality comparison based on contained value."""
        if isinstance(other, ModelContainer):
            return bool(self.value == other.value)
        return bool(self.value == other)

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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Note: Previously had type aliases (StringContainer, IntContainer, etc.)
# These were removed to comply with ONEX strong typing standards.
# Use explicit generic types instead: ModelContainer[str], ModelContainer[int], etc.


# Note: Previously had factory functions (string_container, int_container, etc.)
# These were removed to comply with ONEX strong typing standards.
# Use explicit creation: ModelContainer.create(value, container_type, ...)


# Export for use
__all__ = [
    "ModelContainer",
]
