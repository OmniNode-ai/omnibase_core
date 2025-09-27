"""
Analytics Error Tracking Model.

Error and warning tracking for analytics collections.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .model_analytics_error_summary import ModelAnalyticsErrorSummary


class ModelAnalyticsErrorTracking(BaseModel):
    """
    Error and warning tracking for analytics collections.

    Focused on error counting and severity management.
    """

    # Error tracking
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")
    critical_error_count: int = Field(
        default=0,
        description="Number of critical errors",
    )

    @property
    def total_issues(self) -> int:
        """Get total count of all issues."""
        return self.error_count + self.warning_count + self.critical_error_count

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return self.error_count > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return self.warning_count > 0

    @property
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        return self.critical_error_count > 0

    @property
    def has_any_issues(self) -> bool:
        """Check if there are any issues at all."""
        return self.total_issues > 0

    def get_error_severity_level(self) -> str:
        """Get descriptive error severity level."""
        if self.critical_error_count > 0:
            return "Critical"
        elif self.error_count > 10:
            return "High"
        elif self.error_count > 5:
            return "Medium"
        elif self.error_count > 0:
            return "Low"
        elif self.warning_count > 0:
            return "Warnings Only"
        else:
            return "Clean"

    def calculate_error_rate(self, total_invocations: int) -> float:
        """Calculate error rate percentage."""
        if total_invocations == 0:
            return 0.0
        return (self.error_count / total_invocations) * 100.0

    def calculate_critical_error_rate(self, total_invocations: int) -> float:
        """Calculate critical error rate percentage."""
        if total_invocations == 0:
            return 0.0
        return (self.critical_error_count / total_invocations) * 100.0

    def is_error_rate_acceptable(
        self, total_invocations: int, threshold: float = 5.0
    ) -> bool:
        """Check if error rate is below acceptable threshold."""
        return self.calculate_error_rate(total_invocations) <= threshold

    def update_error_counts(
        self,
        errors: int,
        warnings: int,
        critical_errors: int,
    ) -> None:
        """Update all error counts."""
        self.error_count = max(0, errors)
        self.warning_count = max(0, warnings)
        self.critical_error_count = max(0, critical_errors)

    def add_errors(
        self,
        errors: int = 0,
        warnings: int = 0,
        critical_errors: int = 0,
    ) -> None:
        """Add to existing error counts."""
        self.error_count += max(0, errors)
        self.warning_count += max(0, warnings)
        self.critical_error_count += max(0, critical_errors)

    def increment_error(self) -> None:
        """Increment error count by 1."""
        self.error_count += 1

    def increment_warning(self) -> None:
        """Increment warning count by 1."""
        self.warning_count += 1

    def increment_critical_error(self) -> None:
        """Increment critical error count by 1."""
        self.critical_error_count += 1

    def clear_all_errors(self) -> None:
        """Clear all error and warning counts."""
        self.error_count = 0
        self.warning_count = 0
        self.critical_error_count = 0

    def get_error_distribution(self) -> dict[str, int]:
        """Get error distribution."""
        return {
            "errors": self.error_count,
            "warnings": self.warning_count,
            "critical_errors": self.critical_error_count,
        }

    def get_error_summary(
        self, total_invocations: int = 0
    ) -> ModelAnalyticsErrorSummary:
        """Get comprehensive error summary."""
        return ModelAnalyticsErrorSummary.create_summary(
            total_issues=self.total_issues,
            error_count=self.error_count,
            warning_count=self.warning_count,
            critical_error_count=self.critical_error_count,
            error_rate_percentage=self.calculate_error_rate(total_invocations),
            critical_error_rate_percentage=self.calculate_critical_error_rate(
                total_invocations
            ),
            severity_level=self.get_error_severity_level(),
            has_critical_issues=self.has_critical_errors,
        )

    @classmethod
    def create_clean(cls) -> ModelAnalyticsErrorTracking:
        """Create error tracking with no errors."""
        return cls()

    @classmethod
    def create_with_warnings(cls, warning_count: int) -> ModelAnalyticsErrorTracking:
        """Create error tracking with only warnings."""
        return cls(warning_count=warning_count)

    @classmethod
    def create_with_errors(
        cls,
        error_count: int,
        warning_count: int = 0,
        critical_error_count: int = 0,
    ) -> ModelAnalyticsErrorTracking:
        """Create error tracking with specified error counts."""
        return cls(
            error_count=error_count,
            warning_count=warning_count,
            critical_error_count=critical_error_count,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelAnalyticsErrorTracking"]
