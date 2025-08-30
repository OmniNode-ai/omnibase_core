"""
Validation Error Model

Structured validation error model for argument parsing and validation
with severity levels and detailed error information.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_severity import ModelSeverity


class ModelValidationError(BaseModel):
    """
    Structured validation error for argument parsing and validation.

    This model provides detailed information about validation failures
    including location, severity, and suggested fixes.
    """

    error_code: str = Field(
        ...,
        description="Unique error code for this validation error",
        pattern="^[A-Z][A-Z0-9_]*$",
    )

    message: str = Field(..., description="Human-readable error message")

    field_name: str | None = Field(
        None,
        description="Name of the field that failed validation",
    )

    field_value: Any | None = Field(None, description="Value that failed validation")

    severity: ModelSeverity = Field(
        default_factory=ModelSeverity.ERROR,
        description="Severity level of this validation error",
    )

    location: str | None = Field(
        None,
        description="Location where the error occurred (e.g., 'argument 2', 'flag --name')",
    )

    expected_type: str | None = Field(
        None,
        description="Expected type or format for the field",
    )

    actual_type: str | None = Field(
        None,
        description="Actual type or format that was provided",
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested fixes or alternatives",
    )

    validation_rule: str | None = Field(
        None,
        description="The validation rule that was violated",
    )

    help_text: str | None = Field(
        None,
        description="Additional help text for resolving the error",
    )

    def is_critical(self) -> bool:
        """Check if this is a critical validation error."""
        return self.severity.name in ["CRITICAL", "FATAL"]

    def is_warning(self) -> bool:
        """Check if this is just a warning."""
        return self.severity.name == "WARNING"

    def get_display_message(self) -> str:
        """Get formatted display message for CLI output."""
        parts = []

        # Add severity prefix
        if self.severity.name == "FATAL":
            parts.append("FATAL:")
        elif self.severity.name == "CRITICAL":
            parts.append("CRITICAL:")
        elif self.severity.name == "ERROR":
            parts.append("ERROR:")
        elif self.severity.name == "WARNING":
            parts.append("WARNING:")

        # Add location if available
        if self.location:
            parts.append(f"[{self.location}]")

        # Add main message
        parts.append(self.message)

        # Add type information if available
        if self.expected_type and self.actual_type:
            parts.append(f"(expected {self.expected_type}, got {self.actual_type})")

        return " ".join(parts)

    def get_help_display(self) -> str | None:
        """Get formatted help display with suggestions."""
        if not self.suggestions and not self.help_text:
            return None

        parts = []

        if self.help_text:
            parts.append(f"Help: {self.help_text}")

        if self.suggestions:
            parts.append("Suggestions:")
            for suggestion in self.suggestions:
                parts.append(f"  - {suggestion}")

        return "\n".join(parts)

    @classmethod
    def create_type_error(
        cls,
        field_name: str,
        expected_type: str,
        actual_value: Any,
        location: str | None = None,
    ) -> "ModelValidationError":
        """Create a type validation error."""
        actual_type = type(actual_value).__name__
        return cls(
            error_code="TYPE_MISMATCH",
            message=f"Invalid type for {field_name}",
            field_name=field_name,
            field_value=actual_value,
            severity=ModelSeverity.ERROR(),
            location=location,
            expected_type=expected_type,
            actual_type=actual_type,
            suggestions=[f"Provide a {expected_type} value for {field_name}"],
        )

    @classmethod
    def create_required_error(
        cls,
        field_name: str,
        location: str | None = None,
    ) -> "ModelValidationError":
        """Create a required field error."""
        return cls(
            error_code="REQUIRED_FIELD",
            message=f"Required argument '{field_name}' is missing",
            field_name=field_name,
            severity=ModelSeverity.ERROR(),
            location=location,
            suggestions=[f"Provide the required --{field_name} argument"],
        )

    @classmethod
    def create_choice_error(
        cls,
        field_name: str,
        actual_value: Any,
        valid_choices: list[str],
        location: str | None = None,
    ) -> "ModelValidationError":
        """Create a choice validation error."""
        return cls(
            error_code="INVALID_CHOICE",
            message=f"Invalid choice '{actual_value}' for {field_name}",
            field_name=field_name,
            field_value=actual_value,
            severity=ModelSeverity.ERROR(),
            location=location,
            suggestions=[f"Use one of: {', '.join(valid_choices)}"],
        )

    @classmethod
    def create_pattern_error(
        cls,
        field_name: str,
        actual_value: Any,
        pattern: str,
        location: str | None = None,
    ) -> "ModelValidationError":
        """Create a pattern validation error."""
        return cls(
            error_code="PATTERN_MISMATCH",
            message=f"Value '{actual_value}' for {field_name} does not match required pattern",
            field_name=field_name,
            field_value=actual_value,
            severity=ModelSeverity.ERROR(),
            location=location,
            validation_rule=f"Pattern: {pattern}",
            suggestions=[f"Ensure {field_name} matches the pattern: {pattern}"],
        )
