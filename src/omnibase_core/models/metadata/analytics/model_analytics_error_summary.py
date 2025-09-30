"""
Analytics Error Summary Model.

Structured error summary data for analytics.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelAnalyticsErrorSummary(BaseModel):
    """
    Structured error summary for analytics.

    Replaces primitive soup unions with typed fields.
    Implements omnibase_spi protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Count metrics
    total_issues: int = Field(description="Total number of issues")
    error_count: int = Field(description="Number of errors")
    warning_count: int = Field(description="Number of warnings")
    critical_error_count: int = Field(description="Number of critical errors")

    # Rate metrics (percentages)
    error_rate_percentage: float = Field(description="Error rate as percentage")
    critical_error_rate_percentage: float = Field(
        description="Critical error rate as percentage",
    )

    # Status indicators
    severity_level: str = Field(description="Overall severity level")
    has_critical_issues: bool = Field(description="Whether there are critical issues")

    @property
    def has_any_issues(self) -> bool:
        """Check if there are any issues at all."""
        return self.total_issues > 0

    @property
    def is_error_free(self) -> bool:
        """Check if there are no errors (only warnings allowed)."""
        return self.error_count == 0 and self.critical_error_count == 0

    @property
    def has_warnings_only(self) -> bool:
        """Check if there are only warnings (no errors)."""
        return (
            self.warning_count > 0
            and self.error_count == 0
            and self.critical_error_count == 0
        )

    def get_overall_health_status(self) -> str:
        """Get overall health status based on error counts."""
        if self.critical_error_count > 0:
            return "Critical"
        if self.error_count > 0:
            return "Poor"
        if self.warning_count > 0:
            return "Fair"
        return "Excellent"

    def get_issue_breakdown(self) -> dict[str, int]:
        """Get breakdown of issue counts by type."""
        return {
            "critical": self.critical_error_count,
            "errors": self.error_count,
            "warnings": self.warning_count,
        }

    @classmethod
    def create_summary(
        cls,
        total_issues: int,
        error_count: int,
        warning_count: int,
        critical_error_count: int,
        error_rate_percentage: float,
        critical_error_rate_percentage: float,
        severity_level: str,
        has_critical_issues: bool,
    ) -> ModelAnalyticsErrorSummary:
        """Create an error summary with all required data."""
        return cls(
            total_issues=total_issues,
            error_count=error_count,
            warning_count=warning_count,
            critical_error_count=critical_error_count,
            error_rate_percentage=error_rate_percentage,
            critical_error_rate_percentage=critical_error_rate_percentage,
            severity_level=severity_level,
            has_critical_issues=has_critical_issues,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelAnalyticsErrorSummary"]
