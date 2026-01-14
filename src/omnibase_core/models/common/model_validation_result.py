from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)

__all__ = [
    "ModelValidationIssue",
    "ModelValidationMetadata",
    "ModelValidationResult",
]

"""
Consolidated Validation Result Model

Unified ONEX-compatible model for all validation operations across the codebase.
Uses strong typing with no fallbacks - Path objects, not strings; specific types, not Any.

This replaces:
- omnibase_core.model.core.model_validation_result
- omnibase_core.model.generation.model_validation_result
- omnibase_core.model.security.model_validation_result
- omnibase_core.model.validation.model_validation_result
"""


class ModelValidationResult[T: object](BaseModel):
    """
    Unified validation result model for all ONEX components.

    This model provides:
    - Strong typing with generic support for validated values
    - Comprehensive issue tracking with severity levels
    - Rich metadata about the validation process
    - Helper methods for common validation patterns
    - Current standards with all previous implementations
    """

    # Mutable model: allows add_issue(), merge() mutations. Uses extra="forbid" for
    # internal consistency. from_attributes=True for pytest-xdist compatibility.
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    # Core validation result
    is_valid: bool = Field(default=False, description="Overall validation result")

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
    def error_level_count(self) -> int:
        """Number of ERROR-severity issues."""
        return len(self.get_issues_by_severity(EnumSeverity.ERROR))

    @property
    def warning_count(self) -> int:
        """Number of warning-level issues."""
        return len(self.get_issues_by_severity(EnumSeverity.WARNING))

    @property
    def critical_count(self) -> int:
        """Number of critical-level issues."""
        return len(self.get_issues_by_severity(EnumSeverity.CRITICAL))

    @property
    def fatal_count(self) -> int:
        """Number of fatal-level issues."""
        return len(self.get_issues_by_severity(EnumSeverity.FATAL))

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
        final_issues: list[ModelValidationIssue] = issues if issues is not None else []

        if errors:
            # Convert legacy errors to issues
            for error_msg in errors:
                final_issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.ERROR,
                        message=error_msg,
                    )
                )

        if summary is None:
            summary = f"Validation failed with {len(final_issues)} issues"

        return cls(
            is_valid=False,
            issues=final_issues,
            errors=errors if errors is not None else [],
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
        severity: EnumSeverity,
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
        # FATAL, CRITICAL, and ERROR all invalidate the result
        if severity in [EnumSeverity.FATAL, EnumSeverity.CRITICAL, EnumSeverity.ERROR]:
            self.is_valid = False

        # Update legacy fields for current standards
        if severity == EnumSeverity.ERROR:
            self.errors.append(message)
        elif severity == EnumSeverity.WARNING:
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
            EnumSeverity.ERROR,
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
            EnumSeverity.WARNING,
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
        return any(issue.severity == EnumSeverity.CRITICAL for issue in self.issues)

    def has_fatal_issues(self) -> bool:
        """Check if there are any fatal issues."""
        return any(issue.severity == EnumSeverity.FATAL for issue in self.issues)

    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.severity == EnumSeverity.ERROR for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(issue.severity == EnumSeverity.WARNING for issue in self.issues)

    def get_issues_by_severity(
        self,
        severity: EnumSeverity,
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
