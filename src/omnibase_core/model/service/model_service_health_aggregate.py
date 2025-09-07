"""
Service Health Aggregate Model.

Provides strongly typed models for aggregated service health information,
replacing Dict[str, Any] patterns with proper Pydantic models.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.model.service.model_service_health import ModelServiceHealth


class HealthSummaryStatus(str, Enum):
    """Overall health summary status."""

    ALL_HEALTHY = "all_healthy"
    PARTIAL_HEALTHY = "partial_healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ModelServiceHealthSummary(BaseModel):
    """
    Summary statistics for service health.
    
    Replaces loose typing in service health aggregation.
    """

    total_services: int = Field(..., description="Total number of services", ge=0)
    healthy_services: int = Field(..., description="Number of healthy services", ge=0)
    unhealthy_services: int = Field(
        ..., description="Number of unhealthy services", ge=0
    )
    degraded_services: int = Field(
        ..., description="Number of degraded services", ge=0
    )
    unknown_services: int = Field(
        ..., description="Number of services with unknown status", ge=0
    )
    overall_status: HealthSummaryStatus = Field(
        ..., description="Overall health status"
    )
    average_response_time_ms: Optional[float] = Field(
        None, description="Average response time across all services"
    )
    last_check_timestamp: datetime = Field(
        ..., description="Timestamp of last health check"
    )


class ModelServiceHealthAggregate(BaseModel):
    """
    Aggregated service health information.
    
    Replaces: Dict[str, Any] in ProtocolServiceResolver.get_all_service_health()
    """

    summary: ModelServiceHealthSummary = Field(
        ..., description="Health summary statistics"
    )
    services: dict[str, ModelServiceHealth] = Field(
        ..., description="Individual service health statuses"
    )
    check_timestamp: datetime = Field(
        default_factory=datetime.now, description="When this aggregate was created"
    )
    check_duration_ms: Optional[int] = Field(
        None, description="Time taken to check all services"
    )
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered during health checks"
    )

    def calculate_summary(self) -> ModelServiceHealthSummary:
        """Calculate summary statistics from individual service health."""
        healthy = sum(1 for s in self.services.values() if s.is_healthy())
        unhealthy = sum(1 for s in self.services.values() if s.is_unhealthy())
        degraded = sum(1 for s in self.services.values() if s.is_degraded())
        unknown = len(self.services) - healthy - unhealthy - degraded

        response_times = [
            s.response_time_ms
            for s in self.services.values()
            if s.response_time_ms is not None
        ]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else None
        )

        if unhealthy > 0 or len(self.errors) > 0:
            overall_status = HealthSummaryStatus.CRITICAL
        elif degraded > 0:
            overall_status = HealthSummaryStatus.DEGRADED
        elif healthy == len(self.services):
            overall_status = HealthSummaryStatus.ALL_HEALTHY
        elif healthy > 0:
            overall_status = HealthSummaryStatus.PARTIAL_HEALTHY
        else:
            overall_status = HealthSummaryStatus.UNKNOWN

        return ModelServiceHealthSummary(
            total_services=len(self.services),
            healthy_services=healthy,
            unhealthy_services=unhealthy,
            degraded_services=degraded,
            unknown_services=unknown,
            overall_status=overall_status,
            average_response_time_ms=avg_response_time,
            last_check_timestamp=self.check_timestamp,
        )