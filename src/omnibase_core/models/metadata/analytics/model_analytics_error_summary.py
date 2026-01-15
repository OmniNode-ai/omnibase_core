"""
Analytics Error Summary Model.

Structured error summary data for analytics.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelAnalyticsErrorSummary(BaseModel):
    """
    Structured error summary for analytics.

    Replaces primitive soup unions with typed fields.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Count metrics
    total_issues: int = Field(description="Total number of issues")
    error_level_count: int = Field(description="Number of ERROR-severity issues")
    warning_count: int = Field(description="Number of warnings")
    critical_error_count: int = Field(description="Number of critical errors")
    fatal_error_count: int = Field(default=0, description="Number of fatal errors")

    # Rate metrics (percentages)
    error_rate_percentage: float = Field(description="Error rate as percentage")
    critical_error_rate_percentage: float = Field(
        description="Critical error rate as percentage",
    )
    fatal_error_rate_percentage: float = Field(
        default=0.0,
        description="Fatal error rate as percentage",
    )

    # Status indicators
    severity_level: EnumSeverity = Field(description="Overall severity level")
    has_critical_issues: bool = Field(description="Whether there are critical issues")
    has_fatal_issues: bool = Field(
        default=False, description="Whether there are fatal issues"
    )

    @property
    def has_any_issues(self) -> bool:
        """Check if there are any issues at all."""
        return self.total_issues > 0

    @property
    def is_error_free(self) -> bool:
        """Check if there are no errors (only warnings allowed)."""
        return (
            self.error_level_count == 0
            and self.critical_error_count == 0
            and self.fatal_error_count == 0
        )

    @property
    def has_warnings_only(self) -> bool:
        """Check if there are only warnings (no errors)."""
        return (
            self.warning_count > 0
            and self.error_level_count == 0
            and self.critical_error_count == 0
            and self.fatal_error_count == 0
        )

    def get_overall_health_status(self) -> str:
        """Get overall health status based on error counts."""
        if self.fatal_error_count > 0:
            return "Fatal"
        if self.critical_error_count > 0:
            return "Critical"
        if self.error_level_count > 0:
            return "Poor"
        if self.warning_count > 0:
            return "Fair"
        return "Excellent"

    def get_issue_breakdown(self) -> dict[str, int]:
        """Get breakdown of issue counts by type."""
        return {
            "fatal": self.fatal_error_count,
            "critical": self.critical_error_count,
            "error_level": self.error_level_count,
            "warnings": self.warning_count,
        }

    @classmethod
    def create_summary(
        cls,
        total_issues: int,
        error_level_count: int,
        warning_count: int,
        critical_error_count: int,
        error_rate_percentage: float,
        critical_error_rate_percentage: float,
        severity_level: EnumSeverity,
        has_critical_issues: bool,
        fatal_error_count: int = 0,
        fatal_error_rate_percentage: float = 0.0,
        has_fatal_issues: bool = False,
    ) -> ModelAnalyticsErrorSummary:
        """Create an error summary with all required data."""
        return cls(
            total_issues=total_issues,
            error_level_count=error_level_count,
            warning_count=warning_count,
            critical_error_count=critical_error_count,
            fatal_error_count=fatal_error_count,
            error_rate_percentage=error_rate_percentage,
            critical_error_rate_percentage=critical_error_rate_percentage,
            fatal_error_rate_percentage=fatal_error_rate_percentage,
            severity_level=severity_level,
            has_critical_issues=has_critical_issues,
            has_fatal_issues=has_fatal_issues,
        )

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Analytics models don't have standard name/description/version fields
        # Pack all error summary data into metadata
        result["metadata"] = {
            "total_issues": self.total_issues,
            "error_level_count": self.error_level_count,
            "warning_count": self.warning_count,
            "critical_error_count": self.critical_error_count,
            "fatal_error_count": self.fatal_error_count,
            "error_rate_percentage": self.error_rate_percentage,
            "critical_error_rate_percentage": self.critical_error_rate_percentage,
            "fatal_error_rate_percentage": self.fatal_error_rate_percentage,
            "severity_level": str(self.severity_level),
            "has_critical_issues": self.has_critical_issues,
            "has_fatal_issues": self.has_fatal_issues,
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


# Export for use
__all__ = ["ModelAnalyticsErrorSummary"]
