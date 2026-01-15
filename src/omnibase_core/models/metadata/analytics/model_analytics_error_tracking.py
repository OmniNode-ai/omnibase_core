"""
Analytics Error Tracking Model.

Error and warning tracking for analytics collections.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_analytics_error_summary import ModelAnalyticsErrorSummary


class ModelAnalyticsErrorTracking(BaseModel):
    """
    Error and warning tracking for analytics collections.

    Focused on error counting and severity management.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Error tracking
    error_level_count: int = Field(
        default=0, description="Number of ERROR-severity issues"
    )
    warning_count: int = Field(default=0, description="Number of warnings")
    critical_error_count: int = Field(
        default=0,
        description="Number of critical errors",
    )
    fatal_error_count: int = Field(
        default=0,
        description="Number of fatal errors",
    )

    @property
    def total_issues(self) -> int:
        """Get total count of all issues."""
        return (
            self.error_level_count
            + self.warning_count
            + self.critical_error_count
            + self.fatal_error_count
        )

    @property
    def has_errors(self) -> bool:
        """Check if there are any ERROR-severity issues."""
        return self.error_level_count > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return self.warning_count > 0

    @property
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        return self.critical_error_count > 0

    @property
    def has_fatal_errors(self) -> bool:
        """Check if there are any fatal errors."""
        return self.fatal_error_count > 0

    @property
    def has_any_issues(self) -> bool:
        """Check if there are any issues at all."""
        return self.total_issues > 0

    def get_error_severity_level(self) -> EnumSeverity:
        """Get error severity level as EnumSeverity.

        Mapping:
        - Fatal errors present → FATAL
        - Critical errors present → CRITICAL
        - >10 ERROR-severity issues → ERROR (high severity)
        - >5 ERROR-severity issues → WARNING (medium severity)
        - >0 ERROR-severity issues → INFO (low severity)
        - Warnings only → WARNING
        - Clean (no issues) → DEBUG
        """
        if self.fatal_error_count > 0:
            return EnumSeverity.FATAL
        if self.critical_error_count > 0:
            return EnumSeverity.CRITICAL
        if self.error_level_count > 10:
            return EnumSeverity.ERROR
        if self.error_level_count > 5:
            return EnumSeverity.WARNING
        if self.error_level_count > 0:
            return EnumSeverity.INFO
        if self.warning_count > 0:
            return EnumSeverity.WARNING
        return EnumSeverity.DEBUG

    def calculate_error_rate(self, total_invocations: int) -> float:
        """Calculate ERROR-severity issue rate percentage."""
        if total_invocations == 0:
            return 0.0
        return (self.error_level_count / total_invocations) * 100.0

    def calculate_critical_error_rate(self, total_invocations: int) -> float:
        """Calculate critical error rate percentage."""
        if total_invocations == 0:
            return 0.0
        return (self.critical_error_count / total_invocations) * 100.0

    def calculate_fatal_error_rate(self, total_invocations: int) -> float:
        """Calculate fatal error rate percentage."""
        if total_invocations == 0:
            return 0.0
        return (self.fatal_error_count / total_invocations) * 100.0

    def is_error_rate_acceptable(
        self,
        total_invocations: int,
        threshold: float = 5.0,
    ) -> bool:
        """Check if error rate is below acceptable threshold."""
        return self.calculate_error_rate(total_invocations) <= threshold

    def update_error_counts(
        self,
        errors: int,
        warnings: int,
        critical_errors: int,
        fatal_errors: int = 0,
    ) -> None:
        """Update all error counts."""
        self.error_level_count = max(0, errors)
        self.warning_count = max(0, warnings)
        self.critical_error_count = max(0, critical_errors)
        self.fatal_error_count = max(0, fatal_errors)

    def add_errors(
        self,
        errors: int = 0,
        warnings: int = 0,
        critical_errors: int = 0,
        fatal_errors: int = 0,
    ) -> None:
        """Add to existing error counts."""
        self.error_level_count += max(0, errors)
        self.warning_count += max(0, warnings)
        self.critical_error_count += max(0, critical_errors)
        self.fatal_error_count += max(0, fatal_errors)

    def increment_error(self) -> None:
        """Increment ERROR-severity count by 1."""
        self.error_level_count += 1

    def increment_warning(self) -> None:
        """Increment warning count by 1."""
        self.warning_count += 1

    def increment_critical_error(self) -> None:
        """Increment critical error count by 1."""
        self.critical_error_count += 1

    def increment_fatal_error(self) -> None:
        """Increment fatal error count by 1."""
        self.fatal_error_count += 1

    def clear_all_errors(self) -> None:
        """Clear all error and warning counts."""
        self.error_level_count = 0
        self.warning_count = 0
        self.critical_error_count = 0
        self.fatal_error_count = 0

    def get_error_distribution(self) -> dict[str, int]:
        """Get error distribution by severity level."""
        return {
            "error_level": self.error_level_count,
            "warnings": self.warning_count,
            "critical_errors": self.critical_error_count,
            "fatal_errors": self.fatal_error_count,
        }

    def get_error_summary(
        self,
        total_invocations: int = 0,
    ) -> ModelAnalyticsErrorSummary:
        """Get comprehensive error summary."""
        return ModelAnalyticsErrorSummary.create_summary(
            total_issues=self.total_issues,
            error_level_count=self.error_level_count,
            warning_count=self.warning_count,
            critical_error_count=self.critical_error_count,
            fatal_error_count=self.fatal_error_count,
            error_rate_percentage=self.calculate_error_rate(total_invocations),
            critical_error_rate_percentage=self.calculate_critical_error_rate(
                total_invocations,
            ),
            fatal_error_rate_percentage=self.calculate_fatal_error_rate(
                total_invocations,
            ),
            severity_level=self.get_error_severity_level(),
            has_critical_issues=self.has_critical_errors,
            has_fatal_issues=self.has_fatal_errors,
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
        error_level_count: int,
        warning_count: int = 0,
        critical_error_count: int = 0,
        fatal_error_count: int = 0,
    ) -> ModelAnalyticsErrorTracking:
        """Create error tracking with specified error counts."""
        return cls(
            error_level_count=error_level_count,
            warning_count=warning_count,
            critical_error_count=critical_error_count,
            fatal_error_count=fatal_error_count,
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
        # Pack all error tracking data into metadata
        result["metadata"] = {
            "error_level_count": self.error_level_count,
            "warning_count": self.warning_count,
            "critical_error_count": self.critical_error_count,
            "fatal_error_count": self.fatal_error_count,
            "total_issues": self.total_issues,
            "severity_level": str(self.get_error_severity_level()),
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
__all__ = ["ModelAnalyticsErrorTracking"]
