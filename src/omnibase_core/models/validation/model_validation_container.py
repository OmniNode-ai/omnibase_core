"""
Generic validation error aggregator to standardize validation across all domains.

This container provides a unified approach to validation error collection,
aggregation, and reporting that replaces scattered validation logic across
the codebase.
"""

from typing import Optional

from pydantic import BaseModel, Field

from .model_validation_error import ModelValidationError


class ModelValidationContainer(BaseModel):
    """
    Generic container for validation results and error aggregation.

    This model standardizes validation error collection across all domains,
    replacing scattered validation_errors lists and providing consistent
    validation reporting capabilities.
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
        field: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[dict[str, str | int | bool]] = None,
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

    def add_critical_error(
        self,
        message: str,
        field: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[dict[str, str | int | bool]] = None,
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
        return [error for error in self.errors if error.field_name == field_name]

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

    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return not self.has_errors()

    def merge_from(self, other: "ModelValidationContainer") -> None:
        """Merge validation results from another container."""
        self.extend_errors(other.errors)
        self.extend_warnings(other.warnings)

    # Use .model_dump() for serialization - no to_dict() method needed
    # Pydantic provides native serialization via .model_dump()


class ModelValidationBase(BaseModel):
    """
    Mixin for models that need validation capabilities.

    This provides a standard validation container and common validation
    methods that can be inherited by any model requiring validation.
    """

    validation: ModelValidationContainer = Field(
        default_factory=ModelValidationContainer,
        description="Validation results container",
    )

    def is_valid(self) -> bool:
        """Check if model is valid (no validation errors)."""
        return self.validation.is_valid()

    def has_validation_errors(self) -> bool:
        """Check if there are validation errors."""
        return self.validation.has_errors()

    def has_critical_validation_errors(self) -> bool:
        """Check if there are critical validation errors."""
        return self.validation.has_critical_errors()

    def add_validation_error(
        self,
        message: str,
        field: Optional[str] = None,
        error_code: Optional[str] = None,
        critical: bool = False,
    ) -> None:
        """Add a validation error to this model."""
        if critical:
            self.validation.add_critical_error(message, field, error_code)
        else:
            self.validation.add_error(message, field, error_code)

    def add_validation_warning(self, message: str) -> None:
        """Add a validation warning to this model."""
        self.validation.add_warning(message)

    def get_validation_summary(self) -> str:
        """Get validation summary for this model."""
        return self.validation.get_error_summary()

    def validate_model_data(self) -> None:
        """
        Override in subclasses for custom validation logic.

        This method should populate the validation container with
        any errors or warnings found during validation.
        """
        pass

    def perform_validation(self) -> bool:
        """
        Perform validation and return success status.

        This calls validate_model_data() and returns True if no errors.
        """
        # Clear previous validation results
        self.validation.clear_all()

        # Run custom validation
        self.validate_model_data()

        # Return success status
        return self.is_valid()


# Export for use
__all__ = ["ModelValidationContainer", "ModelValidationBase"]
