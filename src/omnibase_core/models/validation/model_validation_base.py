"""
Mixin for models that need validation capabilities.

This provides a standard validation container and common validation
methods that can be inherited by any model requiring validation.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .model_validation_container import ModelValidationContainer


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
__all__ = ["ModelValidationBase"]
