"""
Validation error model for tracking validation failures.
"""

from typing import Any

from pydantic import BaseModel, Field

from ...enums.enum_validation_severity import EnumValidationSeverity

# Compatibility alias for existing code
ValidationSeverity = EnumValidationSeverity


class ModelValidationError(BaseModel):
    """Validation error information."""

    message: str = Field(..., description="Error message")
    severity: EnumValidationSeverity = Field(
        default=EnumValidationSeverity.ERROR,
        description="Error severity level",
    )
    field_name: str | None = Field(
        default=None,
        description="Field name that caused the error",
    )
    error_code: str | None = Field(
        default=None,
        description="Error code for programmatic handling",
    )
    details: dict[str, str | int | bool] | None = Field(
        default=None,
        description="Additional error details",
    )
    line_number: int | None = Field(
        default=None,
        description="Line number where error occurred",
    )
    column_number: int | None = Field(
        default=None,
        description="Column number where error occurred",
    )

    def is_critical(self) -> bool:
        """Check if this is a critical error."""
        return bool(self.severity == EnumValidationSeverity.CRITICAL)

    def is_error(self) -> bool:
        """Check if this is an error (error or critical)."""
        return bool(
            self.severity
            in [
                EnumValidationSeverity.ERROR,
                EnumValidationSeverity.CRITICAL,
            ]
        )

    def is_warning(self) -> bool:
        """Check if this is a warning."""
        return bool(self.severity == EnumValidationSeverity.WARNING)

    def is_info(self) -> bool:
        """Check if this is an info message."""
        return bool(self.severity == EnumValidationSeverity.INFO)

    @classmethod
    def create_error(
        cls,
        message: str,
        field_name: str | None = None,
        error_code: str | None = None,
    ) -> "ModelValidationError":
        """Create a standard error."""
        return cls(
            message=message,
            severity=EnumValidationSeverity.ERROR,
            field_name=field_name,
            error_code=error_code,
        )

    @classmethod
    def create_critical(
        cls,
        message: str,
        field_name: str | None = None,
        error_code: str | None = None,
    ) -> "ModelValidationError":
        """Create a critical error."""
        return cls(
            message=message,
            severity=EnumValidationSeverity.CRITICAL,
            field_name=field_name,
            error_code=error_code,
        )

    @classmethod
    def create_warning(
        cls,
        message: str,
        field_name: str | None = None,
        error_code: str | None = None,
    ) -> "ModelValidationError":
        """Create a warning."""
        return cls(
            message=message,
            severity=EnumValidationSeverity.WARNING,
            field_name=field_name,
            error_code=error_code,
        )
