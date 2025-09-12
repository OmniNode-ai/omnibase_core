"""
Enterprise Registry Resolution Result Model.

This module provides comprehensive registry resolution result tracking with business intelligence,
performance analytics, and operational insights for ONEX registry resolution systems.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from omnibase_core.models.core.model_audit_entry import ModelAuditEntry
    from omnibase_core.models.core.model_business_impact import ModelBusinessImpact
    from omnibase_core.models.core.model_generic_metadata import ModelGenericMetadata
    from omnibase_core.models.core.model_generic_properties import ModelErrorSummary
    from omnibase_core.models.core.model_monitoring_metrics import (
        ModelMonitoringMetrics,
    )

from .model_registry_resolution_context import ModelRegistryResolutionContext


class ResolutionStatus(str, Enum):
    """Registry resolution status values."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CACHED = "cached"
    RETRY_REQUIRED = "retry_required"


class ResolutionPerformance(str, Enum):
    """Registry resolution performance categories."""

    EXCELLENT = "excellent"  # < 1s
    GOOD = "good"  # 1-5s
    ACCEPTABLE = "acceptable"  # 5-15s
    SLOW = "slow"  # 15-30s
    VERY_SLOW = "very_slow"  # > 30s


class ModelRegistryResolutionResult(BaseModel):
    """
    Enterprise-grade registry resolution result with comprehensive tracking,
    analytics, and operational insights.

    Features:
    - Comprehensive resolution tracking and analytics
    - Performance monitoring and optimization insights
    - Error analysis and recovery recommendations
    - Business intelligence and operational metrics
    - Audit trail and compliance reporting
    - Cache management and optimization
    - Factory methods for common scenarios
    """

    registry: Any = Field(..., description="The resolved registry instance")

    resolution_context: ModelRegistryResolutionContext = Field(
        ...,
        description="Context used for resolution",
    )

    resolution_log: list[str] = Field(
        default_factory=list,
        description="Log of resolution steps for audit and debugging",
    )

    status: ResolutionStatus | None = Field(
        default=ResolutionStatus.SUCCESS,
        description="Overall resolution status",
    )

    start_time: str | None = Field(
        default=None,
        description="ISO timestamp when resolution started",
    )

    end_time: str | None = Field(
        default=None,
        description="ISO timestamp when resolution completed",
    )

    duration_ms: int | None = Field(
        default=None,
        description="Resolution duration in milliseconds",
        ge=0,
    )

    cached_result: bool | None = Field(
        default=False,
        description="Whether this result was served from cache",
    )

    retry_count: int | None = Field(
        default=0,
        description="Number of retries performed",
        ge=0,
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if resolution failed",
        max_length=1000,
    )

    error_code: str | None = Field(
        default=None,
        description="Specific error code for programmatic handling",
        max_length=50,
    )

    warnings: list[str] | None = Field(
        default_factory=list,
        description="Non-fatal warnings during resolution",
    )

    performance_metrics: Optional["ModelMonitoringMetrics"] = Field(
        None,
        description="Detailed performance and resource metrics",
    )

    registry_metadata: Optional["ModelGenericMetadata"] = Field(
        None,
        description="Metadata about the resolved registry",
    )

    cache_metadata: Optional["ModelGenericMetadata"] = Field(
        None,
        description="Cache-related metadata and statistics",
    )

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timestamps(cls, v: str | None) -> str | None:
        """Validate ISO timestamp format."""
        if v is None:
            return v

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            msg = "Timestamp must be a valid ISO timestamp"
            raise ValueError(msg)

    # === Status and Success Analysis ===

    def is_successful(self) -> bool:
        """Check if the resolution was successful."""
        return self.status in [ResolutionStatus.SUCCESS, ResolutionStatus.CACHED]

    def is_failed(self) -> bool:
        """Check if the resolution failed."""
        return self.status in [ResolutionStatus.FAILURE, ResolutionStatus.TIMEOUT]

    def is_partial_success(self) -> bool:
        """Check if the resolution was partially successful."""
        return self.status == ResolutionStatus.PARTIAL_SUCCESS

    def requires_retry(self) -> bool:
        """Check if the resolution requires retry."""
        return self.status == ResolutionStatus.RETRY_REQUIRED

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return bool(self.warnings)

    def get_success_rate(self) -> float:
        """Get success rate considering retries (0.0 to 1.0)."""
        if self.is_successful():
            # Success on first try gets 1.0, success with retries gets lower score
            if self.retry_count == 0:
                return 1.0
            # Penalize based on retry count
            penalty = min(self.retry_count * 0.1, 0.5)
            return 1.0 - penalty
        if self.is_partial_success():
            return 0.7
        return 0.0

    # === Performance Analysis ===

    def get_duration_seconds(self) -> float | None:
        """Get resolution duration in seconds."""
        if self.duration_ms is None:
            return None
        return self.duration_ms / 1000.0

    def get_performance_category(self) -> ResolutionPerformance:
        """Categorize performance based on duration."""
        if self.duration_ms is None:
            return ResolutionPerformance.ACCEPTABLE

        seconds = self.get_duration_seconds()

        if seconds < 1:
            return ResolutionPerformance.EXCELLENT
        if seconds < 5:
            return ResolutionPerformance.GOOD
        if seconds < 15:
            return ResolutionPerformance.ACCEPTABLE
        if seconds < 30:
            return ResolutionPerformance.SLOW
        return ResolutionPerformance.VERY_SLOW

    def is_performance_concerning(self) -> bool:
        """Check if performance indicates potential issues."""
        return self.get_performance_category() in [
            ResolutionPerformance.SLOW,
            ResolutionPerformance.VERY_SLOW,
        ]

    def get_performance_score(self) -> float:
        """Get performance score (0.0 to 1.0)."""
        category = self.get_performance_category()

        score_map = {
            ResolutionPerformance.EXCELLENT: 1.0,
            ResolutionPerformance.GOOD: 0.8,
            ResolutionPerformance.ACCEPTABLE: 0.6,
            ResolutionPerformance.SLOW: 0.3,
            ResolutionPerformance.VERY_SLOW: 0.1,
        }

        base_score = score_map[category]

        # Adjust for cache hits (bonus)
        if self.cached_result:
            base_score = min(1.0, base_score + 0.2)

        # Adjust for retries (penalty)
        if self.retry_count:
            penalty = min(self.retry_count * 0.1, 0.3)
            base_score = max(0.0, base_score - penalty)

        return base_score

    def get_duration_human(self) -> str:
        """Get human-readable duration."""
        if self.duration_ms is None:
            return "unknown"

        if self.duration_ms < 1000:
            return f"{self.duration_ms}ms"
        seconds = self.duration_ms / 1000
        return f"{seconds:.2f}s"

    # === Cache Analysis ===

    def was_cached(self) -> bool:
        """Check if result was served from cache."""
        return self.cached_result or self.status == ResolutionStatus.CACHED

    def get_cache_efficiency(self) -> float | None:
        """Get cache efficiency score if applicable."""
        if not self.was_cached():
            return None

        # Cache efficiency is excellent if very fast
        if self.duration_ms and self.duration_ms < 100:
            return 1.0
        if self.duration_ms and self.duration_ms < 500:
            return 0.8
        return 0.6

    def should_update_cache(self) -> bool:
        """Determine if cache should be updated with this result."""
        return (
            self.is_successful()
            and not self.was_cached()
            and self.resolution_context.should_use_cache()
        )

    # === Error and Issue Analysis ===

    def get_error_summary(self) -> Optional["ModelErrorSummary"]:
        """Get comprehensive error summary."""
        if not self.is_failed() and not self.error_message:
            return None

        from omnibase_core.models.core.model_generic_properties import ModelErrorSummary

        return ModelErrorSummary(
            code=self.error_code,
            message=self.error_message or "Unknown error",
            details={
                "status": self.status.value,
                "retry_count": self.retry_count,
                "has_warnings": self.has_warnings(),
                "warning_count": len(self.warnings) if self.warnings else 0,
                "warnings": self.warnings[:5] if self.warnings else [],
            },
        )

    def get_resolution_issues(self) -> list[str]:
        """Get list of all issues encountered during resolution."""
        issues = []

        if self.error_message:
            issues.append(f"Error: {self.error_message}")

        if self.retry_count > 0:
            issues.append(f"Required {self.retry_count} retries")

        if self.is_performance_concerning():
            duration = self.get_duration_human()
            issues.append(f"Performance concern: {duration} duration")

        if self.warnings:
            issues.extend([f"Warning: {warning}" for warning in self.warnings])

        return issues

    def get_recovery_recommendations(self) -> list[str]:
        """Get recovery recommendations based on resolution issues."""
        recommendations = []

        if self.status == ResolutionStatus.TIMEOUT:
            recommendations.append(
                "Increase resolution timeout or optimize dependencies",
            )

        if self.retry_count > 2:
            recommendations.append("Investigate root cause of resolution failures")

        if self.is_performance_concerning() and not self.was_cached():
            recommendations.append("Enable caching to improve performance")

        if self.error_code:
            recommendations.append(
                f"Check documentation for error code: {self.error_code}",
            )

        if not self.resolution_context.validation_enabled:
            recommendations.append("Enable validation to catch configuration issues")

        return recommendations

    # === Business Intelligence ===

    def calculate_reliability_score(self) -> float:
        """Calculate overall reliability score (0.0 to 1.0)."""
        # Base score from success rate
        reliability_score = self.get_success_rate()

        # Factor in performance
        performance_score = self.get_performance_score()
        reliability_score = (reliability_score * 0.7) + (performance_score * 0.3)

        # Penalize for warnings
        if self.warnings:
            warning_penalty = min(len(self.warnings) * 0.05, 0.2)
            reliability_score *= 1.0 - warning_penalty

        return max(0.0, min(1.0, reliability_score))

    def get_business_impact(self) -> "ModelBusinessImpact":
        """Assess business impact of the resolution result."""
        from omnibase_core.models.core.model_business_impact import (
            ImpactSeverity,
            ModelBusinessImpact,
        )

        # Determine severity based on status
        if self.is_failed():
            severity = ImpactSeverity.CRITICAL
        elif self.requires_retry() or self.retry_count > 2:
            severity = ImpactSeverity.HIGH
        elif self.is_partial_success() or self.has_warnings():
            severity = ImpactSeverity.MEDIUM
        elif self.is_performance_concerning():
            severity = ImpactSeverity.LOW
        else:
            severity = ImpactSeverity.MINIMAL

        return ModelBusinessImpact(
            severity=severity,
            affected_users=0,  # Would need actual data
            financial_impact=0.0,  # Would need actual data
            operational_impact=self._assess_operational_efficiency(),
            recovery_time_hours=0.0,  # Would need actual data
            description=f"Registry resolution {self.status.value} - {self._assess_performance_impact()}",
            mitigation_available=bool(self.get_recovery_recommendations()),
        )

    def _assess_performance_impact(self) -> str:
        """Assess impact on system performance."""
        if self.is_failed():
            return "high_negative"
        if self.is_performance_concerning():
            return "medium_negative"
        if self.get_performance_category() == ResolutionPerformance.EXCELLENT:
            return "positive"
        return "neutral"

    def _assess_operational_efficiency(self) -> str:
        """Assess operational efficiency."""
        if self.was_cached():
            return "high_efficiency"
        if self.is_successful() and not self.retry_count:
            return "good_efficiency"
        if self.retry_count > 0 or self.has_warnings():
            return "low_efficiency"
        return "poor_efficiency"

    def _assess_user_experience(self) -> str:
        """Assess impact on user experience."""
        if self.is_failed():
            return "very_poor"
        if self.is_partial_success():
            return "poor"
        if self.is_performance_concerning():
            return "degraded"
        if self.get_performance_category() == ResolutionPerformance.EXCELLENT:
            return "excellent"
        return "good"

    # === Monitoring Integration ===

    def get_monitoring_metrics(self) -> "ModelMonitoringMetrics":
        """Get comprehensive metrics for monitoring systems."""
        from omnibase_core.models.core.model_monitoring_metrics import (
            MetricValue,
            ModelMonitoringMetrics,
        )

        custom_metrics = {
            "resolution_id": MetricValue(
                value=self.resolution_context.resolution_id or "unknown",
            ),
            "status": MetricValue(value=self.status.value),
            "is_successful": MetricValue(value=self.is_successful()),
            "is_failed": MetricValue(value=self.is_failed()),
            "success_rate": MetricValue(value=self.get_success_rate()),
            "reliability_score": MetricValue(value=self.calculate_reliability_score()),
            "performance_category": MetricValue(
                value=self.get_performance_category().value,
            ),
            "performance_score": MetricValue(value=self.get_performance_score()),
            "is_performance_concerning": MetricValue(
                value=self.is_performance_concerning(),
            ),
            "was_cached": MetricValue(value=self.was_cached()),
            "retry_count": MetricValue(value=self.retry_count or 0),
            "has_warnings": MetricValue(value=self.has_warnings()),
            "warning_count": MetricValue(
                value=len(self.warnings) if self.warnings else 0,
            ),
        }

        # Add cache efficiency if available
        if cache_eff := self.get_cache_efficiency():
            custom_metrics["cache_efficiency"] = MetricValue(value=cache_eff)

        return ModelMonitoringMetrics(
            response_time_ms=float(self.duration_ms) if self.duration_ms else None,
            success_rate=self.get_success_rate() * 100.0,
            health_score=(
                100.0
                if self.is_successful()
                else 50.0 if self.is_partial_success() else 0.0
            ),
            reliability_score=self.calculate_reliability_score() * 100.0,
            custom_metrics=custom_metrics,
        )

    def get_audit_trail(self) -> list["ModelAuditEntry"]:
        """Get audit trail for compliance and debugging."""
        from omnibase_core.models.core.model_audit_entry import ModelAuditEntry

        audit_entries = []

        # Add start event
        if self.start_time:
            audit_entries.append(
                ModelAuditEntry(
                    timestamp=self.start_time,
                    action="resolution_started",
                    actor="system",
                    resource=f"registry_resolution_{self.resolution_context.resolution_id}",
                    result="initiated",
                    details={
                        "context": self.resolution_context.get_operational_summary(),
                        "dependency_mode": self.resolution_context.get_effective_dependency_mode().value,
                    },
                ),
            )

        # Add each log entry as an audit event
        for log_entry in self.resolution_log:
            # Extract timestamp from log entry if in format [timestamp] message
            if log_entry.startswith("[") and "]" in log_entry:
                timestamp_end = log_entry.index("]")
                timestamp = log_entry[1:timestamp_end]
                message = log_entry[timestamp_end + 2 :]
            else:
                timestamp = self.start_time or datetime.now().isoformat()
                message = log_entry

            audit_entries.append(
                ModelAuditEntry(
                    timestamp=timestamp,
                    action="resolution_log",
                    actor="system",
                    resource=f"registry_resolution_{self.resolution_context.resolution_id}",
                    result="logged",
                    details={"message": message},
                ),
            )

        # Add completion event
        if self.end_time:
            audit_entries.append(
                ModelAuditEntry(
                    timestamp=self.end_time,
                    action="resolution_completed",
                    actor="system",
                    resource=f"registry_resolution_{self.resolution_context.resolution_id}",
                    result=self.status.value,
                    details={
                        "duration_ms": self.duration_ms,
                        "retry_count": self.retry_count,
                        "cached_result": self.cached_result,
                        "warnings": self.warnings,
                        "performance_category": self.get_performance_category().value,
                    },
                ),
            )

        return audit_entries

    # === Logging and Tracking ===

    def add_log_entry(self, message: str, timestamp: str | None = None) -> None:
        """Add a log entry to the resolution process."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        log_entry = f"[{timestamp}] {message}"
        self.resolution_log.append(log_entry)

    def add_warning(self, warning: str) -> None:
        """Add a warning to the resolution result."""
        if self.warnings is None:
            self.warnings = []
        self.warnings.append(warning)
        self.add_log_entry(f"WARNING: {warning}")

    def mark_completed(
        self,
        status: ResolutionStatus = ResolutionStatus.SUCCESS,
    ) -> None:
        """Mark the resolution as completed with timing."""
        self.status = status
        self.end_time = datetime.now().isoformat()

        if self.start_time and self.end_time:
            start_dt = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            duration = end_dt - start_dt
            self.duration_ms = int(duration.total_seconds() * 1000)

        self.add_log_entry(f"Resolution completed with status: {status.value}")

    # === Factory Methods ===

    @classmethod
    def create_success(
        cls,
        registry: Any,
        context: ModelRegistryResolutionContext,
        duration_ms: int | None = None,
        cached: bool = False,
    ) -> "ModelRegistryResolutionResult":
        """Create a successful resolution result."""
        result = cls(
            registry=registry,
            resolution_context=context,
            status=ResolutionStatus.CACHED if cached else ResolutionStatus.SUCCESS,
            start_time=datetime.now().isoformat(),
            cached_result=cached,
            duration_ms=duration_ms,
        )

        result.add_log_entry("Resolution started")
        if cached:
            result.add_log_entry("Result served from cache")
        result.mark_completed(
            ResolutionStatus.CACHED if cached else ResolutionStatus.SUCCESS,
        )

        return result

    @classmethod
    def create_failure(
        cls,
        context: ModelRegistryResolutionContext,
        error_message: str,
        error_code: str | None = None,
        retry_count: int = 0,
    ) -> "ModelRegistryResolutionResult":
        """Create a failed resolution result."""
        result = cls(
            registry=None,  # No registry on failure
            resolution_context=context,
            status=ResolutionStatus.FAILURE,
            start_time=datetime.now().isoformat(),
            error_message=error_message,
            error_code=error_code,
            retry_count=retry_count,
        )

        result.add_log_entry("Resolution started")
        result.add_log_entry(f"Resolution failed: {error_message}")
        if retry_count > 0:
            result.add_log_entry(f"Failed after {retry_count} retries")
        result.mark_completed(ResolutionStatus.FAILURE)

        return result

    @classmethod
    def create_timeout(
        cls,
        context: ModelRegistryResolutionContext,
        timeout_seconds: int,
    ) -> "ModelRegistryResolutionResult":
        """Create a timeout resolution result."""
        result = cls(
            registry=None,
            resolution_context=context,
            status=ResolutionStatus.TIMEOUT,
            start_time=datetime.now().isoformat(),
            error_message=f"Resolution timed out after {timeout_seconds} seconds",
            error_code="RESOLUTION_TIMEOUT",
            duration_ms=timeout_seconds * 1000,
        )

        result.add_log_entry("Resolution started")
        result.add_log_entry(f"Resolution timed out after {timeout_seconds}s")
        result.mark_completed(ResolutionStatus.TIMEOUT)

        return result

    @classmethod
    def create_partial_success(
        cls,
        registry: Any,
        context: ModelRegistryResolutionContext,
        warnings: list[str],
        duration_ms: int | None = None,
    ) -> "ModelRegistryResolutionResult":
        """Create a partial success resolution result."""
        result = cls(
            registry=registry,
            resolution_context=context,
            status=ResolutionStatus.PARTIAL_SUCCESS,
            start_time=datetime.now().isoformat(),
            warnings=warnings,
            duration_ms=duration_ms,
        )

        result.add_log_entry("Resolution started")
        for warning in warnings:
            result.add_log_entry(f"WARNING: {warning}")
        result.mark_completed(ResolutionStatus.PARTIAL_SUCCESS)

        return result
