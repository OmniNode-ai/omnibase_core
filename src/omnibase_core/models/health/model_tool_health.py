"""
Enterprise Tool Health Monitoring Model.

This module provides comprehensive tool health tracking with business intelligence,
performance monitoring, and operational insights for ONEX registry tools.
"""

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from omnibase_core.constants import MAX_DESCRIPTION_LENGTH, MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.enums.enum_tool_type import EnumToolType
from omnibase_core.models.core.model_error_summary import ModelErrorSummary
from omnibase_core.models.discovery.model_metric_value import ModelMetricValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.models.core.model_generic_properties import (
        ModelGenericProperties,
    )
    from omnibase_core.models.core.model_monitoring_metrics import (
        ModelMonitoringMetrics,
    )


class ModelToolHealth(BaseModel):
    """
    Enterprise-grade tool health status tracking with comprehensive monitoring,
    business intelligence, and operational insights.

    Features:
    - Structured health status with business logic
    - Performance metrics and timing analysis
    - Error categorization and recovery recommendations
    - Operational metadata and monitoring integration
    - Business intelligence and reliability scoring
    - Factory methods for common scenarios
    """

    tool_name: str = Field(
        default=...,
        description="Name of the tool",
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    status: EnumHealthStatus = Field(
        default=...,
        description="Current health status of the tool",
    )

    tool_type: EnumToolType = Field(
        default=..., description="Type/category of the tool"
    )

    is_callable: bool = Field(
        default=...,
        description="Whether the tool can be invoked successfully",
    )

    error_message: str | None = Field(
        default=None,
        description="Detailed error message if tool is unhealthy",
        max_length=MAX_DESCRIPTION_LENGTH,
    )

    error_code: str | None = Field(
        default=None,
        description="Specific error code for programmatic handling",
        max_length=50,
    )

    last_check_time: str | None = Field(
        default=None,
        description="ISO timestamp of last health check",
    )

    response_time_ms: int | None = Field(
        default=None,
        description="Response time in milliseconds for health check",
        ge=0,
    )

    consecutive_failures: int | None = Field(
        default=0,
        description="Number of consecutive health check failures",
        ge=0,
    )

    uptime_seconds: int | None = Field(
        default=None,
        description="Tool uptime in seconds",
        ge=0,
    )

    version: ModelSemVer | None = Field(
        default=None,
        description="Tool version if available",
        max_length=50,
    )

    configuration: "ModelGenericProperties | None" = Field(
        default=None,
        description="Tool configuration summary",
    )

    metrics: "ModelMonitoringMetrics | None" = Field(
        default=None,
        description="Performance and operational metrics",
    )

    dependencies: list[str] | None = Field(
        default_factory=list,
        description="List of tool dependencies",
    )

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v or not v.strip():
            msg = "tool_name cannot be empty or whitespace"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        v = v.strip()

        # Check for valid tool name pattern (alphanumeric, underscores, hyphens)
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_\-]*$", v):
            msg = "tool_name must start with letter and contain only alphanumeric, underscore, and hyphen characters"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    @field_validator("error_code")
    @classmethod
    def validate_error_code(cls, v: str | None) -> str | None:
        """Validate error code format."""
        if v is None:
            return v

        v = v.strip().upper()
        if not v:
            return None

        # Basic format validation (alphanumeric with underscores)
        if not re.match(r"^[A-Z0-9_]+$", v):
            msg = "error_code must contain only uppercase letters, numbers, and underscores"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    @field_validator("last_check_time")
    @classmethod
    def validate_last_check_time(cls, v: str | None) -> str | None:
        """Validate ISO timestamp format."""
        if v is None:
            return v

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            msg = "last_check_time must be a valid ISO timestamp"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

    # === Health Status Analysis ===

    def is_healthy(self) -> bool:
        """Check if the tool is in a healthy state."""
        return self.status == EnumHealthStatus.AVAILABLE and self.is_callable

    def is_unhealthy(self) -> bool:
        """Check if the tool is in an unhealthy state."""
        return self.status in [
            EnumHealthStatus.ERROR,
            EnumHealthStatus.UNAVAILABLE,
        ]

    def is_degraded(self) -> bool:
        """Check if the tool is degraded but functional."""
        return self.status == EnumHealthStatus.DEGRADED

    def requires_attention(self) -> bool:
        """Check if the tool requires immediate attention."""
        return (
            self.is_unhealthy()
            or (
                self.consecutive_failures is not None and self.consecutive_failures >= 3
            )
            or (self.response_time_ms is not None and self.response_time_ms > 10000)
        )

    def get_severity_level(self) -> str:
        """Get human-readable severity level."""
        if self.status == EnumHealthStatus.ERROR:
            return "critical"
        if self.status == EnumHealthStatus.UNAVAILABLE:
            return "high"
        if self.status == EnumHealthStatus.DEGRADED:
            return "medium"
        if self.requires_attention():
            return "low"
        return "info"

    # === Performance Analysis ===

    def get_performance_category(self) -> str:
        """Categorize performance based on response time."""
        if not self.response_time_ms:
            return "unknown"

        if self.response_time_ms < 50:
            return "excellent"
        if self.response_time_ms < 200:
            return "good"
        if self.response_time_ms < 1000:
            return "acceptable"
        if self.response_time_ms < 5000:
            return "slow"
        return "very_slow"

    def is_performance_concerning(self) -> bool:
        """Check if performance metrics indicate potential issues."""
        return self.get_performance_category() in ["slow", "very_slow"]

    def get_response_time_human(self) -> str:
        """Get human-readable response time."""
        if not self.response_time_ms:
            return "unknown"

        if self.response_time_ms < 1000:
            return f"{self.response_time_ms}ms"
        seconds = self.response_time_ms / 1000
        return f"{seconds:.2f}s"

    def get_uptime_human(self) -> str:
        """Get human-readable uptime."""
        if not self.uptime_seconds:
            return "unknown"

        if self.uptime_seconds < 60:
            return f"{self.uptime_seconds}s"
        if self.uptime_seconds < 3600:
            minutes = self.uptime_seconds // 60
            return f"{minutes}m"
        if self.uptime_seconds < 86400:
            hours = self.uptime_seconds // 3600
            return f"{hours}h"
        days = self.uptime_seconds // 86400
        return f"{days}d"

    # === Factory Methods ===

    @classmethod
    def create_healthy(
        cls,
        tool_name: str,
        tool_type: str = "utility",
        response_time_ms: int = 50,
        *,
        error_message: str | None = None,
        error_code: str | None = None,
        configuration: "ModelGenericProperties | None" = None,
        metrics: "ModelMonitoringMetrics | None" = None,
        uptime_seconds: int | None = None,
        version: ModelSemVer | None = None,
        dependencies: list[str] | None = None,
    ) -> "ModelToolHealth":
        """Create a healthy tool health status."""
        return cls(
            tool_name=tool_name,
            status=EnumHealthStatus.AVAILABLE,
            tool_type=EnumToolType(tool_type),
            is_callable=True,
            error_message=error_message,
            error_code=error_code,
            last_check_time=datetime.now(UTC).isoformat(),
            response_time_ms=response_time_ms,
            consecutive_failures=0,
            uptime_seconds=uptime_seconds,
            version=version,
            configuration=configuration,
            metrics=metrics,
            dependencies=dependencies if dependencies is not None else [],
        )

    @classmethod
    def create_error(
        cls,
        tool_name: str,
        error_message: str,
        tool_type: str = "utility",
        error_code: str | None = None,
        consecutive_failures: int = 1,
        *,
        configuration: "ModelGenericProperties | None" = None,
        metrics: "ModelMonitoringMetrics | None" = None,
        uptime_seconds: int | None = None,
        version: ModelSemVer | None = None,
        dependencies: list[str] | None = None,
    ) -> "ModelToolHealth":
        """Create an error tool health status."""
        return cls(
            tool_name=tool_name,
            status=EnumHealthStatus.ERROR,
            tool_type=EnumToolType(tool_type),
            is_callable=False,
            error_message=error_message,
            error_code=error_code,
            last_check_time=datetime.now(UTC).isoformat(),
            consecutive_failures=consecutive_failures,
            uptime_seconds=uptime_seconds,
            version=version,
            configuration=configuration,
            metrics=metrics,
            dependencies=dependencies if dependencies is not None else [],
        )

    # === Reliability Analysis ===

    def calculate_reliability_score(self) -> float:
        """Calculate reliability score (0.0 to 1.0) based on health metrics."""
        base_score = 1.0 if self.is_healthy() else 0.0

        # Deduct for consecutive failures
        if self.consecutive_failures:
            failure_penalty = min(self.consecutive_failures * 0.1, 0.5)
            base_score *= 1.0 - failure_penalty

        # Deduct for poor performance
        if self.is_performance_concerning():
            base_score *= 0.8

        # Deduct for error conditions
        if self.status == EnumHealthStatus.ERROR:
            base_score = 0.0
        elif self.status == EnumHealthStatus.DEGRADED:
            base_score *= 0.6

        return max(0.0, min(1.0, base_score))

    def get_availability_category(self) -> str:
        """Get availability category based on consecutive failures."""
        if not self.consecutive_failures:
            return "highly_available"
        if self.consecutive_failures < 2:
            return "available"
        if self.consecutive_failures < 5:
            return "unstable"
        return "unavailable"

    # === Error Analysis ===

    def get_error_summary(self) -> "ModelErrorSummary | None":
        """Get comprehensive error summary."""
        if not self.is_unhealthy() and not self.error_message:
            return None

        return ModelErrorSummary(
            error_code=self.error_code or "TOOL_ERROR",
            error_type=self.status.value,
            error_message=self.error_message or "Tool is unhealthy",
            component=self.tool_name,
            operation=None,
            stack_trace=None,
            error_id=None,
            correlation_id=None,
            has_been_reported=False,
            impact_level=self.get_severity_level(),
            context_data={
                "consecutive_failures": str(self.consecutive_failures),
                "requires_attention": str(self.requires_attention()),
            },
        )

    def get_recovery_recommendations(self) -> list[str]:
        """Get recovery recommendations based on error patterns."""
        recommendations = []

        if self.status == EnumHealthStatus.ERROR:
            recommendations.append(
                "Investigate error logs and restart tool if necessary",
            )

        if self.consecutive_failures and self.consecutive_failures >= 3:
            recommendations.append(
                "Tool has multiple consecutive failures - check dependencies and configuration",
            )

        if self.is_performance_concerning():
            recommendations.append(
                "Performance issues detected - check resource usage and optimize",
            )

        if not self.is_callable:
            recommendations.append(
                "Tool is not callable - verify implementation and dependencies",
            )

        if self.error_code:
            recommendations.append(
                f"Check documentation for error code: {self.error_code}",
            )

        return recommendations

    # === Monitoring Integration ===

    def get_monitoring_metrics(self) -> "ModelMonitoringMetrics":
        """Get metrics suitable for monitoring systems."""
        # Import at runtime to avoid circular import
        from omnibase_core.models.core.model_monitoring_metrics import (
            ModelMonitoringMetrics,
        )

        health_score = (
            100.0 if self.is_healthy() else 50.0 if self.is_degraded() else 0.0
        )
        success_rate = 100.0 if self.is_healthy() else 0.0
        error_rate = 100.0 if self.is_unhealthy() else 0.0

        return ModelMonitoringMetrics(
            throughput_rps=None,
            cpu_usage_percent=None,
            memory_usage_mb=None,
            disk_usage_gb=None,
            network_bandwidth_mbps=None,
            queue_depth=None,
            items_processed=None,
            items_failed=None,
            processing_lag_ms=None,
            response_time_ms=(
                float(self.response_time_ms) if self.response_time_ms else None
            ),
            success_rate=success_rate,
            error_rate=error_rate,
            compliance_score=None,
            reliability_score=self.calculate_reliability_score(),
            health_score=health_score,
            uptime_seconds=self.uptime_seconds,
            availability_percent=self.calculate_reliability_score() * 100.0,
            last_error_timestamp=datetime.now(UTC) if self.is_unhealthy() else None,
            start_time=None,
            end_time=None,
            custom_metrics={
                "tool_name": ModelMetricValue(
                    name="tool_name",
                    value=self.tool_name,
                    metric_type="string",
                ),
                "tool_type": ModelMetricValue(
                    name="tool_type",
                    value=self.tool_type.value,
                    metric_type="string",
                ),
                "is_callable": ModelMetricValue(
                    name="is_callable",
                    value=self.is_callable,
                    metric_type="boolean",
                ),
                "severity": ModelMetricValue(
                    name="severity",
                    value=self.get_severity_level(),
                    metric_type="string",
                ),
                "consecutive_failures": ModelMetricValue(
                    name="consecutive_failures",
                    value=self.consecutive_failures or 0,
                    metric_type="counter",
                ),
            },
        )

    def get_log_context(self) -> dict[str, str]:
        """Get structured logging context."""
        context = {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "tool_type": self.tool_type.value,
            "severity": self.get_severity_level(),
            "is_callable": str(self.is_callable),
        }

        if self.response_time_ms:
            context["response_time"] = self.get_response_time_human()

        if self.error_code:
            context["error_code"] = self.error_code

        if self.version:
            context["version"] = str(self.version)

        return context

    # === Additional Factory Methods ===

    @classmethod
    def create_degraded(
        cls,
        tool_name: str,
        tool_type: str = "utility",
        response_time_ms: int = 2000,
        warning_message: str = "Performance degraded",
        *,
        error_code: str | None = None,
        configuration: "ModelGenericProperties | None" = None,
        metrics: "ModelMonitoringMetrics | None" = None,
        uptime_seconds: int | None = None,
        version: ModelSemVer | None = None,
        dependencies: list[str] | None = None,
    ) -> "ModelToolHealth":
        """Create a degraded tool health status."""
        return cls(
            tool_name=tool_name,
            status=EnumHealthStatus.DEGRADED,
            tool_type=EnumToolType(tool_type),
            is_callable=True,
            error_message=warning_message,
            error_code=error_code,
            last_check_time=datetime.now(UTC).isoformat(),
            response_time_ms=response_time_ms,
            consecutive_failures=0,
            uptime_seconds=uptime_seconds,
            version=version,
            configuration=configuration,
            metrics=metrics,
            dependencies=dependencies if dependencies is not None else [],
        )

    @classmethod
    def create_unavailable(
        cls,
        tool_name: str,
        tool_type: str = "utility",
        reason: str = "Tool unavailable",
        *,
        error_code: str | None = None,
        configuration: "ModelGenericProperties | None" = None,
        metrics: "ModelMonitoringMetrics | None" = None,
        uptime_seconds: int | None = None,
        version: ModelSemVer | None = None,
        dependencies: list[str] | None = None,
    ) -> "ModelToolHealth":
        """Create an unavailable tool health status."""
        return cls(
            tool_name=tool_name,
            status=EnumHealthStatus.UNAVAILABLE,
            tool_type=EnumToolType(tool_type),
            is_callable=False,
            error_message=reason,
            error_code=error_code,
            last_check_time=datetime.now(UTC).isoformat(),
            consecutive_failures=1,
            uptime_seconds=uptime_seconds,
            version=version,
            configuration=configuration,
            metrics=metrics,
            dependencies=dependencies if dependencies is not None else [],
        )

    @classmethod
    def create_with_metrics(
        cls,
        tool_name: str,
        tool_type: str,
        status: str,
        is_callable: bool,
        response_time_ms: int | None = None,
        uptime_seconds: int | None = None,
        version: ModelSemVer | None = None,
        *,
        error_message: str | None = None,
        error_code: str | None = None,
        configuration: "ModelGenericProperties | None" = None,
        metrics: "ModelMonitoringMetrics | None" = None,
        dependencies: list[str] | None = None,
    ) -> "ModelToolHealth":
        """Create tool health with comprehensive metrics."""
        return cls(
            tool_name=tool_name,
            status=EnumHealthStatus(status),
            tool_type=EnumToolType(tool_type),
            is_callable=is_callable,
            error_message=error_message,
            error_code=error_code,
            last_check_time=datetime.now(UTC).isoformat(),
            response_time_ms=response_time_ms,
            uptime_seconds=uptime_seconds,
            version=version,
            consecutive_failures=0 if is_callable else 1,
            configuration=configuration,
            metrics=metrics,
            dependencies=dependencies if dependencies is not None else [],
        )


# Fix forward references for Pydantic models
try:
    ModelToolHealth.model_rebuild()
except (
    Exception
):  # error-ok: model_rebuild may fail during circular import resolution, safe to ignore
    pass
