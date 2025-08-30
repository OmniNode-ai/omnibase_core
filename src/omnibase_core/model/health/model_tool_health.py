"""
Enterprise Tool Health Monitoring Model.

This module provides comprehensive tool health tracking with business intelligence,
performance monitoring, and operational insights for ONEX registry tools.
"""

import re
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from omnibase_core.model.core.model_generic_properties import (
        ModelErrorSummary, ModelGenericProperties)
    from omnibase_core.model.core.model_monitoring_metrics import \
        ModelMonitoringMetrics


class ToolHealthStatus(str, Enum):
    """Standard tool health status values."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    DEGRADED = "degraded"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"


class ToolType(str, Enum):
    """Standard tool type categories."""

    PROCESSOR = "processor"
    VALIDATOR = "validator"
    TRANSFORMER = "transformer"
    CONNECTOR = "connector"
    HANDLER = "handler"
    GENERATOR = "generator"
    ANALYZER = "analyzer"
    UTILITY = "utility"
    CUSTOM = "custom"


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
        ..., description="Name of the tool", min_length=1, max_length=100
    )

    status: ToolHealthStatus = Field(
        ..., description="Current health status of the tool"
    )

    tool_type: ToolType = Field(..., description="Type/category of the tool")

    is_callable: bool = Field(
        ..., description="Whether the tool can be invoked successfully"
    )

    error_message: Optional[str] = Field(
        None, description="Detailed error message if tool is unhealthy", max_length=1000
    )

    error_code: Optional[str] = Field(
        None, description="Specific error code for programmatic handling", max_length=50
    )

    last_check_time: Optional[str] = Field(
        default=None, description="ISO timestamp of last health check"
    )

    response_time_ms: Optional[int] = Field(
        default=None, description="Response time in milliseconds for health check", ge=0
    )

    consecutive_failures: Optional[int] = Field(
        default=0, description="Number of consecutive health check failures", ge=0
    )

    uptime_seconds: Optional[int] = Field(
        default=None, description="Tool uptime in seconds", ge=0
    )

    version: Optional[str] = Field(
        default=None, description="Tool version if available", max_length=50
    )

    configuration: Optional["ModelGenericProperties"] = Field(
        None, description="Tool configuration summary"
    )

    metrics: Optional["ModelMonitoringMetrics"] = Field(
        None, description="Performance and operational metrics"
    )

    dependencies: Optional[List[str]] = Field(
        default_factory=list, description="List of tool dependencies"
    )

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty or whitespace")

        v = v.strip()

        # Check for valid tool name pattern (alphanumeric, underscores, hyphens)
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_\-]*$", v):
            raise ValueError(
                "tool_name must start with letter and contain only alphanumeric, underscore, and hyphen characters"
            )

        return v

    @field_validator("error_code")
    @classmethod
    def validate_error_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate error code format."""
        if v is None:
            return v

        v = v.strip().upper()
        if not v:
            return None

        # Basic format validation (alphanumeric with underscores)
        if not re.match(r"^[A-Z0-9_]+$", v):
            raise ValueError(
                "error_code must contain only uppercase letters, numbers, and underscores"
            )

        return v

    @field_validator("last_check_time")
    @classmethod
    def validate_last_check_time(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO timestamp format."""
        if v is None:
            return v

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("last_check_time must be a valid ISO timestamp")

    # === Health Status Analysis ===

    def is_healthy(self) -> bool:
        """Check if the tool is in a healthy state."""
        return self.status == ToolHealthStatus.AVAILABLE and self.is_callable

    def is_unhealthy(self) -> bool:
        """Check if the tool is in an unhealthy state."""
        return self.status in [ToolHealthStatus.ERROR, ToolHealthStatus.UNAVAILABLE]

    def is_degraded(self) -> bool:
        """Check if the tool is degraded but functional."""
        return self.status == ToolHealthStatus.DEGRADED

    def requires_attention(self) -> bool:
        """Check if the tool requires immediate attention."""
        return (
            self.is_unhealthy()
            or (self.consecutive_failures and self.consecutive_failures >= 3)
            or (self.response_time_ms and self.response_time_ms > 10000)
        )

    def get_severity_level(self) -> str:
        """Get human-readable severity level."""
        if self.status == ToolHealthStatus.ERROR:
            return "critical"
        elif self.status == ToolHealthStatus.UNAVAILABLE:
            return "high"
        elif self.status == ToolHealthStatus.DEGRADED:
            return "medium"
        elif self.requires_attention():
            return "low"
        else:
            return "info"

    # === Performance Analysis ===

    def get_performance_category(self) -> str:
        """Categorize performance based on response time."""
        if not self.response_time_ms:
            return "unknown"

        if self.response_time_ms < 50:
            return "excellent"
        elif self.response_time_ms < 200:
            return "good"
        elif self.response_time_ms < 1000:
            return "acceptable"
        elif self.response_time_ms < 5000:
            return "slow"
        else:
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
        else:
            seconds = self.response_time_ms / 1000
            return f"{seconds:.2f}s"

    def get_uptime_human(self) -> str:
        """Get human-readable uptime."""
        if not self.uptime_seconds:
            return "unknown"

        if self.uptime_seconds < 60:
            return f"{self.uptime_seconds}s"
        elif self.uptime_seconds < 3600:
            minutes = self.uptime_seconds // 60
            return f"{minutes}m"
        elif self.uptime_seconds < 86400:
            hours = self.uptime_seconds // 3600
            return f"{hours}h"
        else:
            days = self.uptime_seconds // 86400
            return f"{days}d"

    # === Factory Methods ===

    @classmethod
    def create_healthy(
        cls, tool_name: str, tool_type: str = "utility", response_time_ms: int = 50
    ) -> "ModelToolHealth":
        """Create a healthy tool health status."""
        return cls(
            tool_name=tool_name,
            status=ToolHealthStatus.AVAILABLE,
            tool_type=ToolType(tool_type),
            is_callable=True,
            last_check_time=datetime.now().isoformat(),
            response_time_ms=response_time_ms,
            consecutive_failures=0,
        )

    @classmethod
    def create_error(
        cls,
        tool_name: str,
        error_message: str,
        tool_type: str = "utility",
        error_code: Optional[str] = None,
        consecutive_failures: int = 1,
    ) -> "ModelToolHealth":
        """Create an error tool health status."""
        return cls(
            tool_name=tool_name,
            status=ToolHealthStatus.ERROR,
            tool_type=ToolType(tool_type),
            is_callable=False,
            error_message=error_message,
            error_code=error_code,
            last_check_time=datetime.now().isoformat(),
            consecutive_failures=consecutive_failures,
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
        if self.status == ToolHealthStatus.ERROR:
            base_score = 0.0
        elif self.status == ToolHealthStatus.DEGRADED:
            base_score *= 0.6

        return max(0.0, min(1.0, base_score))

    def get_availability_category(self) -> str:
        """Get availability category based on consecutive failures."""
        if not self.consecutive_failures:
            return "highly_available"
        elif self.consecutive_failures < 2:
            return "available"
        elif self.consecutive_failures < 5:
            return "unstable"
        else:
            return "unavailable"

    # === Error Analysis ===

    def get_error_summary(self) -> Optional["ModelErrorSummary"]:
        """Get comprehensive error summary."""
        if not self.is_unhealthy() and not self.error_message:
            return None

        from omnibase_core.model.core.model_generic_properties import \
            ModelErrorSummary

        return ModelErrorSummary(
            error_code=self.error_code or "TOOL_ERROR",
            error_type=self.status.value,
            error_message=self.error_message or "Tool is unhealthy",
            component=self.tool_name,
            impact_level=self.get_severity_level(),
            context_data={
                "consecutive_failures": str(self.consecutive_failures),
                "requires_attention": str(self.requires_attention()),
            },
        )

    def get_recovery_recommendations(self) -> List[str]:
        """Get recovery recommendations based on error patterns."""
        recommendations = []

        if self.status == ToolHealthStatus.ERROR:
            recommendations.append(
                "Investigate error logs and restart tool if necessary"
            )

        if self.consecutive_failures and self.consecutive_failures >= 3:
            recommendations.append(
                "Tool has multiple consecutive failures - check dependencies and configuration"
            )

        if self.is_performance_concerning():
            recommendations.append(
                "Performance issues detected - check resource usage and optimize"
            )

        if not self.is_callable:
            recommendations.append(
                "Tool is not callable - verify implementation and dependencies"
            )

        if self.error_code:
            recommendations.append(
                f"Check documentation for error code: {self.error_code}"
            )

        return recommendations

    # === Monitoring Integration ===

    def get_monitoring_metrics(self) -> "ModelMonitoringMetrics":
        """Get metrics suitable for monitoring systems."""
        from omnibase_core.model.core.model_monitoring_metrics import (
            MetricValue, ModelMonitoringMetrics)

        health_score = (
            100.0 if self.is_healthy() else 50.0 if self.is_degraded() else 0.0
        )
        success_rate = 100.0 if self.is_healthy() else 0.0
        error_rate = 100.0 if self.is_unhealthy() else 0.0

        return ModelMonitoringMetrics(
            response_time_ms=(
                float(self.response_time_ms) if self.response_time_ms else None
            ),
            success_rate=success_rate,
            error_rate=error_rate,
            health_score=health_score,
            uptime_seconds=self.uptime_seconds,
            availability_percent=self.calculate_reliability_score() * 100.0,
            custom_metrics={
                "tool_name": MetricValue(value=self.tool_name),
                "tool_type": MetricValue(value=self.tool_type.value),
                "is_callable": MetricValue(value=self.is_callable),
                "severity": MetricValue(value=self.get_severity_level()),
                "consecutive_failures": MetricValue(
                    value=self.consecutive_failures or 0
                ),
            },
        )

    def get_log_context(self) -> Dict[str, str]:
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
            context["version"] = self.version

        return context

    # === Additional Factory Methods ===

    @classmethod
    def create_degraded(
        cls,
        tool_name: str,
        tool_type: str = "utility",
        response_time_ms: int = 2000,
        warning_message: str = "Performance degraded",
    ) -> "ModelToolHealth":
        """Create a degraded tool health status."""
        return cls(
            tool_name=tool_name,
            status=ToolHealthStatus.DEGRADED,
            tool_type=ToolType(tool_type),
            is_callable=True,
            error_message=warning_message,
            last_check_time=datetime.now().isoformat(),
            response_time_ms=response_time_ms,
            consecutive_failures=0,
        )

    @classmethod
    def create_unavailable(
        cls,
        tool_name: str,
        tool_type: str = "utility",
        reason: str = "Tool unavailable",
    ) -> "ModelToolHealth":
        """Create an unavailable tool health status."""
        return cls(
            tool_name=tool_name,
            status=ToolHealthStatus.UNAVAILABLE,
            tool_type=ToolType(tool_type),
            is_callable=False,
            error_message=reason,
            last_check_time=datetime.now().isoformat(),
            consecutive_failures=1,
        )

    @classmethod
    def create_with_metrics(
        cls,
        tool_name: str,
        tool_type: str,
        status: str,
        is_callable: bool,
        response_time_ms: Optional[int] = None,
        uptime_seconds: Optional[int] = None,
        version: Optional[str] = None,
    ) -> "ModelToolHealth":
        """Create tool health with comprehensive metrics."""
        return cls(
            tool_name=tool_name,
            status=ToolHealthStatus(status),
            tool_type=ToolType(tool_type),
            is_callable=is_callable,
            last_check_time=datetime.now().isoformat(),
            response_time_ms=response_time_ms,
            uptime_seconds=uptime_seconds,
            version=version,
            consecutive_failures=0 if is_callable else 1,
        )


# Fix forward references for Pydantic models
try:
    ModelToolHealth.model_rebuild()
except Exception:
    pass  # Ignore rebuild errors during import
