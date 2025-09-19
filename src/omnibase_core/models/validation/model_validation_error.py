"""
Validation error model for tracking validation failures.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Validation error severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ModelValidationError(BaseModel):
    """Validation error information."""

    message: str = Field(..., description="Error message")
    severity: ValidationSeverity = Field(
        default=ValidationSeverity.ERROR,
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
    details: dict[str, Any] | None = Field(
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
        return self.severity == ValidationSeverity.CRITICAL

    def is_error(self) -> bool:
        """Check if this is an error (error or critical)."""
        return self.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]

    def is_warning(self) -> bool:
        """Check if this is a warning."""
        return self.severity == ValidationSeverity.WARNING

    def is_info(self) -> bool:
        """Check if this is an info message."""
        return self.severity == ValidationSeverity.INFO

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
            severity=ValidationSeverity.ERROR,
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
            severity=ValidationSeverity.CRITICAL,
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
            severity=ValidationSeverity.WARNING,
            field_name=field_name,
            error_code=error_code,
        )
