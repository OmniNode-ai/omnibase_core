"""
Generic validation error aggregator to standardize validation across all domains.

This container provides a unified approach to validation error collection,
aggregation, and reporting that replaces scattered validation logic across
the codebase.
"""

from __future__ import annotations

from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_validation_container_serialized import (
    TypedDictValidationContainerSerialized,
)

from .model_validation_error import ModelValidationError
from .model_validation_value import ModelValidationValue


class ModelValidationContainer(BaseModel):
    """
    Generic container for validation results and error aggregation.

    This model standardizes validation error collection across all domains,
    replacing scattered validation_errors list[Any]s and providing consistent
    validation reporting capabilities.
    Implements Core protocols:
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    errors: list[ModelValidationError] = Field(
        default_factory=list,
        description="Validation errors collected during validation",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages that don't prevent operation",
    )

    def add_error(
        self,
        message: str,
        field: str | None = None,
        error_code: str | None = None,
        details: dict[str, ModelValidationValue] | None = None,
    ) -> None:
        """Add a standard validation error."""
        error = ModelValidationError.create_error(
            message=message,
            field_name=field,
            error_code=error_code,
        )
        if details:
            error.details = details
        self.errors.append(error)

    def add_error_with_raw_details(
        self,
        message: str,
        field: str | None = None,
        error_code: str | None = None,
        raw_details: dict[str, object] | None = None,
    ) -> None:
        """Add a standard validation error with automatic conversion of raw details."""
        converted_details = None
        if raw_details:
            converted_details = {
                key: ModelValidationValue.from_any(value)
                for key, value in raw_details.items()
            }

        self.add_error(
            message=message,
            field=field,
            error_code=error_code,
            details=converted_details,
        )

    def add_critical_error(
        self,
        message: str,
        field: str | None = None,
        error_code: str | None = None,
        details: dict[str, ModelValidationValue] | None = None,
    ) -> None:
        """Add a critical validation error."""
        error = ModelValidationError.create_critical(
            message=message,
            field_name=field,
            error_code=error_code,
        )
        if details:
            error.details = details
        self.errors.append(error)

    def add_critical_error_with_raw_details(
        self,
        message: str,
        field: str | None = None,
        error_code: str | None = None,
        raw_details: dict[str, object] | None = None,
    ) -> None:
        """Add a critical validation error with automatic conversion of raw details."""
        converted_details = None
        if raw_details:
            converted_details = {
                key: ModelValidationValue.from_any(value)
                for key, value in raw_details.items()
            }

        self.add_critical_error(
            message=message,
            field=field,
            error_code=error_code,
            details=converted_details,
        )

    def add_warning(self, message: str) -> None:
        """Add a warning message (deduplicated)."""
        if message not in self.warnings:
            self.warnings.append(message)

    def add_validation_error(self, error: ModelValidationError) -> None:
        """Add a pre-constructed validation error."""
        self.errors.append(error)

    def extend_errors(self, errors: list[ModelValidationError]) -> None:
        """Add multiple validation errors at once."""
        self.errors.extend(errors)

    def extend_warnings(self, warnings: list[str]) -> None:
        """Add multiple warnings at once (deduplicated)."""
        for warning in warnings:
            self.add_warning(warning)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        return any(error.is_critical() for error in self.errors)

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def get_error_count(self) -> int:
        """Get total error count."""
        return len(self.errors)

    def get_critical_error_count(self) -> int:
        """Get critical error count."""
        return sum(1 for error in self.errors if error.is_critical())

    def get_warning_count(self) -> int:
        """Get warning count."""
        return len(self.warnings)

    def get_error_summary(self) -> str:
        """Get formatted error summary."""
        if not self.has_errors() and not self.has_warnings():
            return "No validation issues"

        parts = []
        if self.has_errors():
            error_part = f"{self.get_error_count()} error"
            if self.get_error_count() != 1:
                error_part += "s"
            if self.has_critical_errors():
                error_part += f" ({self.get_critical_error_count()} critical)"
            parts.append(error_part)

        if self.has_warnings():
            warning_part = f"{self.get_warning_count()} warning"
            if self.get_warning_count() != 1:
                warning_part += "s"
            parts.append(warning_part)

        return ", ".join(parts)

    def get_all_error_messages(self) -> list[str]:
        """Get all error messages as strings."""
        return [error.message for error in self.errors]

    def get_critical_error_messages(self) -> list[str]:
        """Get all critical error messages."""
        return [error.message for error in self.errors if error.is_critical()]

    def get_errors_by_field(self, field_name: str) -> list[ModelValidationError]:
        """Get all errors for a specific field."""
        return [
            error for error in self.errors if error.field_display_name == field_name
        ]

    def clear_all(self) -> None:
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()

    def clear_errors(self) -> None:
        """Clear only errors, keep warnings."""
        self.errors.clear()

    def clear_warnings(self) -> None:
        """Clear only warnings, keep errors."""
        self.warnings.clear()

    def validate_instance(self) -> bool:
        """Check if validation passed (no errors) (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist and no errors
            return not self.has_errors()
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def merge_from(self, other: ModelValidationContainer) -> None:
        """Merge validation results from another container."""
        self.extend_errors(other.errors)
        self.extend_warnings(other.warnings)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Use .model_dump() for serialization - no to_dict() method needed
    # Pydantic provides native serialization via .model_dump()

    # Protocol method implementations

    def serialize(self) -> TypedDictValidationContainerSerialized:
        """Serialize to dictionary (Serializable protocol)."""
        return cast(
            TypedDictValidationContainerSerialized,
            self.model_dump(exclude_none=False, by_alias=True),
        )


# Export for use
__all__ = ["ModelValidationContainer"]
