"""
Enterprise Registry Health Report Model.

This module provides comprehensive registry health reporting with business intelligence,
aggregated analytics, and operational insights for ONEX registry systems.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from omnibase_core.model.core.model_examples import ModelNodeInformation
from omnibase_core.model.core.model_generic_properties import ModelGenericProperties
from omnibase_core.model.core.model_monitoring_metrics import ModelMonitoringMetrics
from omnibase_core.model.core.model_trend_data import ModelTrendData
from omnibase_core.model.health.model_tool_health import (
    ModelToolHealth,
    ToolHealthStatus,
)
from omnibase_core.model.service.model_service_health import (
    ModelServiceHealth,
    ServiceHealthStatus,
)

from .model_registry_business_impact_summary import ModelRegistryBusinessImpactSummary
from .model_registry_component_performance import ModelRegistryComponentPerformance
from .model_registry_sla_compliance import ModelRegistrySlaCompliance


class RegistryHealthStatus(str, Enum):
    """Standard registry health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"
    CRITICAL = "critical"


class ModelRegistryHealthReport(BaseModel):
    """
    Enterprise-grade complete health report for registry systems with comprehensive
    analytics, business intelligence, and operational insights.

    Features:
    - Aggregated health analytics from tools and services
    - Business intelligence and performance insights
    - Operational recommendations and alerts
    - Trend analysis and predictive metrics
    - Monitoring integration and alerting support
    - Comprehensive reporting for stakeholders
    """

    status: RegistryHealthStatus = Field(
        ...,
        description="Overall health status of the registry",
    )

    tools_count: int = Field(..., description="Total number of registered tools", ge=0)

    tools_health: list[ModelToolHealth] = Field(
        default_factory=list,
        description="Health status of all tools",
    )

    services_health: list[ModelServiceHealth] = Field(
        default_factory=list,
        description="Health status of external services",
    )

    resolution_context_summary: ModelGenericProperties = Field(
        default_factory=ModelGenericProperties,
        description="Summary of resolution context and configuration",
    )

    error_message: str | None = Field(
        None,
        description="Error message if health check failed",
        max_length=1000,
    )

    error_code: str | None = Field(
        None,
        description="Specific error code for programmatic handling",
        max_length=50,
    )

    check_timestamp: str | None = Field(
        default=None,
        description="ISO timestamp when health check was performed",
    )

    check_duration_ms: int | None = Field(
        default=None,
        description="Duration of health check in milliseconds",
        ge=0,
    )

    registry_version: str | None = Field(
        default=None,
        description="Registry version information",
        max_length=50,
    )

    node_information: ModelNodeInformation | None = Field(
        None,
        description="Information about the node hosting this registry",
    )

    performance_metrics: ModelMonitoringMetrics | None = Field(
        None,
        description="Performance and operational metrics",
    )

    trends: ModelTrendData | None = Field(
        None,
        description="Historical trends and pattern analysis",
    )

    alerts: list[str] | None = Field(
        default_factory=list,
        description="Active alerts and recommendations",
    )

    @field_validator("check_timestamp")
    @classmethod
    def validate_check_timestamp(cls, v: str | None) -> str | None:
        """Validate ISO timestamp format."""
        if v is None:
            return v

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            msg = "check_timestamp must be a valid ISO timestamp"
            raise ValueError(msg)

    # === Overall Health Analysis ===

    def is_healthy(self) -> bool:
        """Check if the registry is in a healthy state."""
        return self.status == RegistryHealthStatus.HEALTHY

    def is_critical(self) -> bool:
        """Check if the registry is in a critical state."""
        return self.status == RegistryHealthStatus.CRITICAL

    def requires_immediate_attention(self) -> bool:
        """Check if the registry requires immediate attention."""
        return self.status in [
            RegistryHealthStatus.ERROR,
            RegistryHealthStatus.CRITICAL,
        ]

    def is_operational(self) -> bool:
        """Check if the registry is operational (healthy or degraded)."""
        return self.status in [
            RegistryHealthStatus.HEALTHY,
            RegistryHealthStatus.DEGRADED,
        ]

    # === Tool Health Analytics ===

    def get_healthy_tools_count(self) -> int:
        """Get count of healthy tools."""
        return len([tool for tool in self.tools_health if tool.is_healthy()])

    def get_unhealthy_tools_count(self) -> int:
        """Get count of unhealthy tools."""
        return len([tool for tool in self.tools_health if tool.is_unhealthy()])

    def get_degraded_tools_count(self) -> int:
        """Get count of degraded tools."""
        return len([tool for tool in self.tools_health if tool.is_degraded()])

    def get_tools_health_percentage(self) -> float:
        """Get percentage of healthy tools."""
        if not self.tools_health:
            return 100.0

        healthy_count = self.get_healthy_tools_count()
        return (healthy_count / len(self.tools_health)) * 100.0

    def get_tools_by_status(self, status: ToolHealthStatus) -> list[ModelToolHealth]:
        """Get tools filtered by health status."""
        return [tool for tool in self.tools_health if tool.status == status]

    def get_critical_tools(self) -> list[ModelToolHealth]:
        """Get tools that require immediate attention."""
        return [tool for tool in self.tools_health if tool.requires_attention()]

    # === Service Health Analytics ===

    def get_healthy_services_count(self) -> int:
        """Get count of healthy services."""
        return len(
            [service for service in self.services_health if service.is_healthy()],
        )

    def get_unhealthy_services_count(self) -> int:
        """Get count of unhealthy services."""
        return len(
            [service for service in self.services_health if service.is_unhealthy()],
        )

    def get_services_health_percentage(self) -> float:
        """Get percentage of healthy services."""
        if not self.services_health:
            return 100.0

        healthy_count = self.get_healthy_services_count()
        return (healthy_count / len(self.services_health)) * 100.0

    def get_services_by_status(
        self,
        status: ServiceHealthStatus,
    ) -> list[ModelServiceHealth]:
        """Get services filtered by health status."""
        return [service for service in self.services_health if service.status == status]

    def get_critical_services(self) -> list[ModelServiceHealth]:
        """Get services that require immediate attention."""
        return [
            service for service in self.services_health if service.requires_attention()
        ]

    # === Performance Analysis ===

    def get_average_tool_response_time(self) -> float | None:
        """Get average response time across all tools."""
        response_times = [
            tool.response_time_ms
            for tool in self.tools_health
            if tool.response_time_ms is not None
        ]

        if not response_times:
            return None

        return sum(response_times) / len(response_times)

    def get_average_service_response_time(self) -> float | None:
        """Get average response time across all services."""
        response_times = [
            service.response_time_ms
            for service in self.services_health
            if service.response_time_ms is not None
        ]

        if not response_times:
            return None

        return sum(response_times) / len(response_times)

    def get_slowest_components(
        self,
        limit: int = 5,
    ) -> list[ModelRegistryComponentPerformance]:
        """Get the slowest performing components."""
        components = []

        # Add tools
        for tool in self.tools_health:
            if tool.response_time_ms:
                components.append(
                    ModelRegistryComponentPerformance(
                        name=tool.tool_name,
                        type="tool",
                        category=tool.tool_type.value,
                        response_time_ms=tool.response_time_ms,
                        status=tool.status.value,
                    ),
                )

        # Add services
        for service in self.services_health:
            if service.response_time_ms:
                components.append(
                    ModelRegistryComponentPerformance(
                        name=service.service_name,
                        type="service",
                        category=service.service_type.value,
                        response_time_ms=service.response_time_ms,
                        status=service.status.value,
                    ),
                )

        # Sort by response time and return top N
        components.sort(key=lambda x: x.response_time_ms, reverse=True)
        return components[:limit]

    # === Reliability Analysis ===

    def calculate_overall_reliability_score(self) -> float:
        """Calculate overall reliability score (0.0 to 1.0)."""
        tool_scores = [tool.calculate_reliability_score() for tool in self.tools_health]
        service_scores = [
            service.calculate_reliability_score() for service in self.services_health
        ]

        all_scores = tool_scores + service_scores

        if not all_scores:
            return 1.0

        # Weight calculation: tools and services contribute equally
        overall_score = sum(all_scores) / len(all_scores)

        # Apply penalty for critical status
        if self.status == RegistryHealthStatus.CRITICAL:
            overall_score *= 0.2
        elif self.status == RegistryHealthStatus.ERROR:
            overall_score *= 0.4
        elif self.status == RegistryHealthStatus.DEGRADED:
            overall_score *= 0.7

        return max(0.0, min(1.0, overall_score))

    def get_reliability_category(self) -> str:
        """Get reliability category based on score."""
        score = self.calculate_overall_reliability_score()

        if score >= 0.95:
            return "excellent"
        if score >= 0.85:
            return "good"
        if score >= 0.70:
            return "acceptable"
        if score >= 0.50:
            return "poor"
        return "critical"

    # === Business Intelligence ===

    def get_business_impact_summary(self) -> ModelRegistryBusinessImpactSummary:
        """Get comprehensive business impact assessment."""
        return ModelRegistryBusinessImpactSummary(
            operational_status=self.status.value,
            availability_percentage=self.get_tools_health_percentage(),
            service_availability_percentage=self.get_services_health_percentage(),
            reliability_score=self.calculate_overall_reliability_score(),
            reliability_category=self.get_reliability_category(),
            critical_components_count=len(self.get_critical_tools())
            + len(self.get_critical_services()),
            performance_impact=self._assess_performance_impact(),
            business_continuity_risk=self._assess_business_continuity_risk(),
            sla_compliance=self._assess_sla_compliance(),
        )

    def _assess_performance_impact(self) -> str:
        """Assess impact on overall system performance."""
        avg_tool_time = self.get_average_tool_response_time()
        avg_service_time = self.get_average_service_response_time()

        # Consider both tool and service performance
        concerning_performance = (
            avg_tool_time and avg_tool_time > 1000
        ) or (  # 1 second for tools
            avg_service_time and avg_service_time > 5000
        )  # 5 seconds for services

        if self.is_critical():
            return "high_negative"
        if concerning_performance or not self.is_operational():
            return "medium_negative"
        if self.status == RegistryHealthStatus.DEGRADED:
            return "low_negative"
        return "minimal"

    def _assess_business_continuity_risk(self) -> str:
        """Assess risk to business continuity."""
        critical_count = len(self.get_critical_tools()) + len(
            self.get_critical_services(),
        )
        unhealthy_percentage = 100 - self.get_tools_health_percentage()

        if self.is_critical() or critical_count > 5:
            return "high"
        if not self.is_operational() or critical_count > 2 or unhealthy_percentage > 25:
            return "medium"
        if self.status == RegistryHealthStatus.DEGRADED or critical_count > 0:
            return "low"
        return "minimal"

    def _assess_sla_compliance(self) -> ModelRegistrySlaCompliance:
        """Assess SLA compliance based on health metrics."""
        availability = self.get_tools_health_percentage()
        reliability = self.calculate_overall_reliability_score()

        return ModelRegistrySlaCompliance(
            availability_sla=(
                "met"
                if availability >= 99.0
                else "at_risk" if availability >= 95.0 else "violated"
            ),
            reliability_sla=(
                "met"
                if reliability >= 0.95
                else "at_risk" if reliability >= 0.85 else "violated"
            ),
            performance_sla=self._check_performance_sla(),
            overall_compliance=(
                "compliant"
                if availability >= 99.0 and reliability >= 0.95
                else "non_compliant"
            ),
        )

    def _check_performance_sla(self) -> str:
        """Check performance SLA compliance."""
        avg_tool_time = self.get_average_tool_response_time()
        avg_service_time = self.get_average_service_response_time()

        # SLA thresholds: tools < 500ms, services < 2000ms
        if (avg_tool_time and avg_tool_time > 1000) or (
            avg_service_time and avg_service_time > 5000
        ):
            return "violated"
        if (avg_tool_time and avg_tool_time > 500) or (
            avg_service_time and avg_service_time > 2000
        ):
            return "at_risk"
        return "met"

    # === Monitoring Integration ===

    def get_monitoring_metrics(self) -> ModelMonitoringMetrics:
        """Get comprehensive metrics for monitoring systems."""
        from omnibase_core.model.core.model_monitoring_metrics import MetricValue

        # Calculate averages
        self.get_average_tool_response_time()
        self.get_average_service_response_time()

        # Build custom metrics
        custom_metrics = {
            "registry_status": MetricValue(value=self.status.value),
            "is_healthy": MetricValue(value=self.is_healthy()),
            "is_critical": MetricValue(value=self.is_critical()),
            "is_operational": MetricValue(value=self.is_operational()),
            "requires_attention": MetricValue(
                value=self.requires_immediate_attention(),
            ),
            "tools_total": MetricValue(value=len(self.tools_health)),
            "tools_healthy": MetricValue(value=self.get_healthy_tools_count()),
            "tools_unhealthy": MetricValue(value=self.get_unhealthy_tools_count()),
            "tools_degraded": MetricValue(value=self.get_degraded_tools_count()),
            "tools_health_percentage": MetricValue(
                value=self.get_tools_health_percentage(),
            ),
            "services_total": MetricValue(value=len(self.services_health)),
            "services_healthy": MetricValue(value=self.get_healthy_services_count()),
            "services_unhealthy": MetricValue(
                value=self.get_unhealthy_services_count(),
            ),
            "services_health_percentage": MetricValue(
                value=self.get_services_health_percentage(),
            ),
            "reliability_score": MetricValue(
                value=self.calculate_overall_reliability_score(),
            ),
            "reliability_category": MetricValue(value=self.get_reliability_category()),
            "critical_components": MetricValue(
                value=len(self.get_critical_tools())
                + len(self.get_critical_services()),
            ),
        }

        return ModelMonitoringMetrics(
            response_time_ms=(
                float(self.check_duration_ms) if self.check_duration_ms else None
            ),
            health_score=(
                100.0 if self.is_healthy() else 50.0 if self.is_operational() else 0.0
            ),
            reliability_score=self.calculate_overall_reliability_score() * 100.0,
            custom_metrics=custom_metrics,
        )

    # === Factory Methods ===

    @classmethod
    def create_healthy(
        cls,
        tools_count: int,
        tools_health: list[ModelToolHealth] | None = None,
        services_health: list[ModelServiceHealth] | None = None,
    ) -> "ModelRegistryHealthReport":
        """Create a healthy registry health report."""
        return cls(
            status=RegistryHealthStatus.HEALTHY,
            tools_count=tools_count,
            tools_health=tools_health or [],
            services_health=services_health or [],
            check_timestamp=datetime.now().isoformat(),
            check_duration_ms=100,
        )

    @classmethod
    def create_critical(
        cls,
        tools_count: int,
        error_message: str,
        tools_health: list[ModelToolHealth] | None = None,
        services_health: list[ModelServiceHealth] | None = None,
        error_code: str | None = None,
    ) -> "ModelRegistryHealthReport":
        """Create a critical registry health report."""
        return cls(
            status=RegistryHealthStatus.CRITICAL,
            tools_count=tools_count,
            tools_health=tools_health or [],
            services_health=services_health or [],
            error_message=error_message,
            error_code=error_code,
            check_timestamp=datetime.now().isoformat(),
        )

    @classmethod
    def create_degraded(
        cls,
        tools_count: int,
        degradation_reason: str,
        tools_health: list[ModelToolHealth] | None = None,
        services_health: list[ModelServiceHealth] | None = None,
    ) -> "ModelRegistryHealthReport":
        """Create a degraded registry health report."""
        return cls(
            status=RegistryHealthStatus.DEGRADED,
            tools_count=tools_count,
            tools_health=tools_health or [],
            services_health=services_health or [],
            error_message=degradation_reason,
            check_timestamp=datetime.now().isoformat(),
        )


# Fix forward references for Pydantic models
try:
    ModelToolHealth.model_rebuild()
except Exception:
    pass  # Ignore rebuild errors during import
