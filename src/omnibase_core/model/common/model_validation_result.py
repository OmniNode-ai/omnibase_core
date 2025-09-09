"""
Consolidated Validation Result Model

Unified ONEX-compliant model for all validation operations across the codebase.
Uses strong typing with no fallbacks - Path objects, not strings; specific types, not Any.

This replaces:
- omnibase_core.model.core.model_validation_result
- omnibase_core.model.generation.model_validation_result
- omnibase_core.model.security.model_validation_result
- omnibase_core.model.validation.model_validation_result
"""

from datetime import datetime
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

# Import the existing enum from validation module
from omnibase_core.model.validation.model_validation_rule import EnumValidationSeverity

T = TypeVar("T")


class ModelValidationIssue(BaseModel):
    """
    Individual validation issue with proper typing.

    Represents a specific issue found during validation with
    comprehensive metadata and suggestions.
    """

    severity: EnumValidationSeverity = Field(
        ...,
        description="Severity level of the issue",
    )
    message: str = Field(..., description="Human-readable issue description")
    code: str | None = Field(
        None,
        description="Machine-readable error code for programmatic handling",
    )
    file_path: Path | None = Field(
        None,
        description="Path to file where issue was found (always Path object, never string)",
    )
    line_number: int | None = Field(
        None,
        description="Line number where issue was found",
    )
    column_number: int | None = Field(
        None,
        description="Column number where issue was found",
    )
    rule_name: str | None = Field(
        None,
        description="Name of validation rule that triggered this issue",
    )
    suggestion: str | None = Field(None, description="Suggested fix for the issue")
    context: dict[str, str] | None = Field(
        None,
        description="Additional string context data for the issue (no Any types)",
    )


class ModelValidationMetadata(BaseModel):
    """Metadata about the validation process."""

    validation_type: str | None = Field(
        None,
        description="Type of validation performed (e.g., 'schema', 'security', 'business')",
    )
    duration_ms: int | None = Field(
        None,
        description="Validation duration in milliseconds",
    )
    files_processed: int | None = Field(
        None,
        description="Number of files processed during validation",
    )
    rules_applied: int | None = Field(
        None,
        description="Number of validation rules applied",
    )
    timestamp: str | None = Field(
        None,
        description="ISO timestamp when validation was performed",
    )
    validator_version: str | None = Field(
        None,
        description="Version of the validator used",
    )


class ModelValidationResult(BaseModel, Generic[T]):
    """
    Unified validation result model for all ONEX components.

    This model provides:
    - Strong typing with generic support for validated values
    - Comprehensive issue tracking with severity levels
    - Rich metadata about the validation process
    - Helper methods for common validation patterns
    - Backwards compatibility with all previous implementations
    """

    # Core validation result
    is_valid: bool = Field(..., description="Overall validation result")

    # Optional validated value with generic typing
    validated_value: T | None = Field(
        None,
        description="The validated and potentially normalized value",
    )

    # Issues tracking
    issues: list[ModelValidationIssue] = Field(
        default_factory=list,
        description="List of all validation issues found",
    )

    # Backwards compatibility fields
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages (deprecated, use issues instead)",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning messages (deprecated, use issues instead)",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="List of suggestions (deprecated, use issues instead)",
    )

    # Summary and details
    summary: str = Field(
        default="Validation completed",
        description="Human-readable validation summary",
    )
    details: str | None = Field(
        None,
        description="Additional validation details",
    )

    # Metadata
    metadata: ModelValidationMetadata | None = Field(
        None,
        description="Structured metadata about the validation process",
    )

    @property
    def issues_found(self) -> int:
        """Number of validation issues found."""
        return len(self.issues)

    @property
    def error_count(self) -> int:
        """Number of error-level issues."""
        return len(self.get_issues_by_severity(EnumValidationSeverity.error))

    @property
    def warning_count(self) -> int:
        """Number of warning-level issues."""
        return len(self.get_issues_by_severity(EnumValidationSeverity.warning))

    @property
    def critical_count(self) -> int:
        """Number of critical-level issues."""
        return len(self.get_issues_by_severity(EnumValidationSeverity.critical))

    # Factory methods for common patterns
    @classmethod
    def create_valid(
        cls,
        value: T | None = None,
        summary: str = "Validation passed",
    ) -> "ModelValidationResult[T]":
        """Create a successful validation result."""
        return cls(
            is_valid=True,
            validated_value=value,
            issues=[],
            summary=summary,
        )

    @classmethod
    def create_invalid(
        cls,
        errors: list[str] | None = None,
        issues: list[ModelValidationIssue] | None = None,
        summary: str | None = None,
    ) -> "ModelValidationResult[T]":
        """Create a failed validation result."""
        # Handle both legacy errors list and new issues list
        final_issues = issues or []

        if errors:
            # Convert legacy errors to issues
            for error_msg in errors:
                final_issues.append(
                    ModelValidationIssue(
                        severity=EnumValidationSeverity.error,
                        message=error_msg,
                    )
                )

        if summary is None:
            summary = f"Validation failed with {len(final_issues)} issues"

        return cls(
            is_valid=False,
            issues=final_issues,
            errors=errors or [],
            summary=summary,
        )

    @classmethod
    def create_success(
        cls,
        summary: str = "Validation passed",
    ) -> "ModelValidationResult[T]":
        """Alias for create_valid for backwards compatibility."""
        return cls.create_valid(summary=summary)

    @classmethod
    def create_failure(
        cls,
        issues: list[ModelValidationIssue],
        summary: str | None = None,
    ) -> "ModelValidationResult[T]":
        """Create a failed validation result with issues."""
        return cls.create_invalid(issues=issues, summary=summary)

    # Helper methods
    def add_issue(
        self,
        severity: EnumValidationSeverity,
        message: str,
        **kwargs: str,
    ) -> None:
        """Add a validation issue to the result."""
        issue = ModelValidationIssue(severity=severity, message=message, **kwargs)
        self.issues.append(issue)

        # Update validity based on severity
        if severity in [EnumValidationSeverity.error, EnumValidationSeverity.critical]:
            self.is_valid = False

        # Update legacy fields for backwards compatibility
        if severity == EnumValidationSeverity.error:
            self.errors.append(message)
        elif severity == EnumValidationSeverity.warning:
            self.warnings.append(message)

        if kwargs.get("suggestion"):
            self.suggestions.append(kwargs["suggestion"])

    def add_error(self, error: str, **kwargs: str) -> None:
        """Add an error to the validation result (backwards compatibility)."""
        self.add_issue(EnumValidationSeverity.error, error, **kwargs)

    def add_warning(self, warning: str, **kwargs: str) -> None:
        """Add a warning to the validation result (backwards compatibility)."""
        self.add_issue(EnumValidationSeverity.warning, warning, **kwargs)

    def add_suggestion(self, suggestion: str) -> None:
        """Add a suggestion to the validation result (backwards compatibility)."""
        self.suggestions.append(suggestion)

    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(
            issue.severity == EnumValidationSeverity.critical for issue in self.issues
        )

    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(
            issue.severity == EnumValidationSeverity.error for issue in self.issues
        )

    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(
            issue.severity == EnumValidationSeverity.warning for issue in self.issues
        )

    def get_issues_by_severity(
        self,
        severity: EnumValidationSeverity,
    ) -> list[ModelValidationIssue]:
        """Get all issues of a specific severity level."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_file(self, file_path: str) -> list[ModelValidationIssue]:
        """Get all issues for a specific file."""
        return [issue for issue in self.issues if issue.file_path == file_path]

    def merge(self, other: "ModelValidationResult") -> None:
        """Merge another validation result into this one."""
        self.issues.extend(other.issues)
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.suggestions.extend(other.suggestions)

        # Update validity
        if not other.is_valid:
            self.is_valid = False

        # Update summary
        if not self.is_valid:
            self.summary = f"Validation failed with {self.issues_found} total issues"
