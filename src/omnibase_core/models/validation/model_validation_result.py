"""
Validation Result Model

Structured model for validation results that replaces Dict[str, Any] usage.
"""

from pydantic import BaseModel, Field

from .model_validation_rule import EnumValidationSeverity


class ModelValidationIssue(BaseModel):
    """
    Individual validation issue.

    Represents a specific issue found during validation with
    proper typing and metadata.
    """

    severity: EnumValidationSeverity = Field(
        ...,
        description="Severity level of the issue",
    )
    message: str = Field(..., description="Human-readable issue description")
    file_path: str | None = Field(
        None,
        description="Path to file where issue was found",
    )
    line_number: int | None = Field(
        None,
        description="Line number where issue was found",
    )
    rule_name: str | None = Field(
        None,
        description="Name of validation rule that triggered this issue",
    )
    suggestion: str | None = Field(None, description="Suggested fix for the issue")


class ModelValidationResult(BaseModel):
    """
    Structured validation result model.

    Replaces Dict[str, Any] usage with proper typing for
    validation results across all ONEX nodes.
    """

    is_valid: bool = Field(..., description="Overall validation result")
    issues_found: int = Field(
        default=0,
        description="Number of validation issues found",
    )
    issues: list[ModelValidationIssue] = Field(
        default_factory=list,
        description="List of validation issues",
    )
    summary: str = Field(..., description="Human-readable validation summary")

    # Optional metadata
    validation_type: str | None = Field(
        None,
        description="Type of validation performed",
    )
    duration_ms: int | None = Field(
        None,
        description="Validation duration in milliseconds",
    )
    files_processed: int | None = Field(
        None,
        description="Number of files processed",
    )

    @classmethod
    def create_success(
        cls,
        summary: str = "Validation passed",
    ) -> "ModelValidationResult":
        """Factory method for successful validation results."""
        return cls(is_valid=True, issues_found=0, issues=[], summary=summary)

    @classmethod
    def create_failure(
        cls,
        issues: list[ModelValidationIssue],
        summary: str | None = None,
    ) -> "ModelValidationResult":
        """Factory method for failed validation results."""
        if summary is None:
            summary = f"Validation failed with {len(issues)} issues"

        return cls(
            is_valid=False,
            issues_found=len(issues),
            issues=issues,
            summary=summary,
        )

    def add_issue(
        self,
        severity: EnumValidationSeverity,
        message: str,
        **kwargs,
    ) -> None:
        """Add a validation issue to the result."""
        issue = ModelValidationIssue(severity=severity, message=message, **kwargs)
        self.issues.append(issue)
        self.issues_found = len(self.issues)

        # Update overall validity based on severity
        if severity in [EnumValidationSeverity.error, EnumValidationSeverity.critical]:
            self.is_valid = False

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

    def get_issues_by_severity(
        self,
        severity: EnumValidationSeverity,
    ) -> list[ModelValidationIssue]:
        """Get all issues of a specific severity level."""
        return [issue for issue in self.issues if issue.severity == severity]
