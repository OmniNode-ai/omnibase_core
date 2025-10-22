from pathlib import Path
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)

__all__ = [
    "ModelValidationIssue",
    "ModelValidationMetadata",
    "ModelValidationResult",
    "T",
    "add_error",
    "add_issue",
    "add_suggestion",
    "add_warning",
    "create_failure",
    "create_invalid",
    "create_success",
    "create_valid",
    "critical_count",
    "details",
    "error_count",
    "errors",
    "final_issues",
    "get_issues_by_file",
    "get_issues_by_severity",
    "has_critical_issues",
    "has_errors",
    "has_warnings",
    "is_valid",
    "issue",
    "issues",
    "issues_found",
    "merge",
    "metadata",
    "suggestions",
    "summary",
    "validated_value",
    "warning_count",
    "warnings",
]

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

# TypeVar with constraints for better type safety
T = TypeVar("T", bound=object)


class ModelValidationResult(BaseModel, Generic[T]):
    """
    Unified validation result model for all ONEX components.

    This model provides:
    - Strong typing with generic support for validated values
    - Comprehensive issue tracking with severity levels
    - Rich metadata about the validation process
    - Helper methods for common validation patterns
    - Current standards with all previous implementations
    """

    # Core validation result
    is_valid: bool = Field(default=..., description="Overall validation result")

    # Optional validated value with generic typing
    validated_value: T | None = Field(
        default=None,
        description="The validated and potentially normalized value",
    )

    # Issues tracking
    issues: list[ModelValidationIssue] = Field(
        default_factory=list,
        description="List of all validation issues found",
    )

    # Current standards fields
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
        default=None,
        description="Additional validation details",
    )

    # Metadata
    metadata: ModelValidationMetadata | None = Field(
        default=None,
        description="Structured metadata about the validation process",
    )

    @property
    def issues_found(self) -> int:
        """Number of validation issues found."""
        return len(self.issues)

    @property
    def error_count(self) -> int:
        """Number of error-level issues."""
        return len(self.get_issues_by_severity(EnumValidationSeverity.ERROR))

    @property
    def warning_count(self) -> int:
        """Number of warning-level issues."""
        return len(self.get_issues_by_severity(EnumValidationSeverity.WARNING))

    @property
    def critical_count(self) -> int:
        """Number of critical-level issues."""
        return len(self.get_issues_by_severity(EnumValidationSeverity.CRITICAL))

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
        final_issues: list[ModelValidationIssue] = issues or []

        if errors:
            # Convert legacy errors to issues
            for error_msg in errors:
                final_issues.append(
                    ModelValidationIssue(
                        severity=EnumValidationSeverity.ERROR,
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
        """Alias for create_valid for current standards."""
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
        code: str | None = None,
        file_path: Path | None = None,
        line_number: int | None = None,
        column_number: int | None = None,
        rule_name: str | None = None,
        suggestion: str | None = None,
        context: dict[str, str] | None = None,
    ) -> None:
        """Add a validation issue to the result."""
        issue = ModelValidationIssue(
            severity=severity,
            message=message,
            code=code,
            file_path=file_path,
            line_number=line_number,
            column_number=column_number,
            rule_name=rule_name,
            suggestion=suggestion,
            context=context,
        )
        self.issues.append(issue)

        # Update validity based on severity
        if severity in [EnumValidationSeverity.ERROR, EnumValidationSeverity.CRITICAL]:
            self.is_valid = False

        # Update legacy fields for current standards
        if severity == EnumValidationSeverity.ERROR:
            self.errors.append(message)
        elif severity == EnumValidationSeverity.WARNING:
            self.warnings.append(message)

        if suggestion:
            self.suggestions.append(suggestion)

    def add_error(
        self,
        error: str,
        code: str | None = None,
        file_path: Path | None = None,
        line_number: int | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Add an error to the validation result (current standards)."""
        self.add_issue(
            EnumValidationSeverity.ERROR,
            error,
            code=code,
            file_path=file_path,
            line_number=line_number,
            suggestion=suggestion,
        )

    def add_warning(
        self,
        warning: str,
        code: str | None = None,
        file_path: Path | None = None,
        line_number: int | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Add a warning to the validation result (current standards)."""
        self.add_issue(
            EnumValidationSeverity.WARNING,
            warning,
            code=code,
            file_path=file_path,
            line_number=line_number,
            suggestion=suggestion,
        )

    def add_suggestion(self, suggestion: str) -> None:
        """Add a suggestion to the validation result (current standards)."""
        self.suggestions.append(suggestion)

    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(
            issue.severity == EnumValidationSeverity.CRITICAL for issue in self.issues
        )

    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(
            issue.severity == EnumValidationSeverity.ERROR for issue in self.issues
        )

    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(
            issue.severity == EnumValidationSeverity.WARNING for issue in self.issues
        )

    def get_issues_by_severity(
        self,
        severity: EnumValidationSeverity,
    ) -> list[ModelValidationIssue]:
        """Get all issues of a specific severity level."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_file(self, file_path: str) -> list[ModelValidationIssue]:
        """Get all issues for a specific file."""
        return [
            issue
            for issue in self.issues
            if issue.file_path is not None and str(issue.file_path) == file_path
        ]

    def merge(self, other: "ModelValidationResult[T]") -> None:
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
        else:
            self.summary = f"Validation completed with {self.issues_found} issues"

        # Update metadata if available
        if other.metadata and self.metadata:
            # Merge metadata by summing counts where applicable
            if other.metadata.files_processed is not None:
                self.metadata.files_processed = (
                    self.metadata.files_processed or 0
                ) + other.metadata.files_processed

            if other.metadata.rules_applied is not None:
                self.metadata.rules_applied = (
                    self.metadata.rules_applied or 0
                ) + other.metadata.rules_applied

            if other.metadata.duration_ms is not None:
                self.metadata.duration_ms = (
                    self.metadata.duration_ms or 0
                ) + other.metadata.duration_ms
        elif other.metadata and not self.metadata:
            # Copy other's metadata if we don't have any
            self.metadata = other.metadata
