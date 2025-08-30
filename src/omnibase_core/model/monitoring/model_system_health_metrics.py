"""
Model for system health metrics.

System-wide health metrics for monitoring.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.monitoring.enum_system_health import EnumSystemHealth


class ModelSystemHealthMetrics(BaseModel):
    """System-wide health metrics."""

    api_availability: float = Field(
        ..., ge=0, le=100, description="API availability percentage"
    )
    database_connectivity: bool = Field(..., description="Database connection status")
    event_bus_latency_ms: float = Field(
        ..., ge=0, description="Event bus latency in milliseconds"
    )

    total_throughput_per_hour: int = Field(
        0, ge=0, description="Total system throughput per hour"
    )
    aggregate_success_rate: float = Field(
        0.0, ge=0, le=100, description="System-wide success rate"
    )
    system_efficiency: float = Field(
        0.0, ge=0, le=100, description="Overall system efficiency"
    )
    cost_per_task: float = Field(0.0, ge=0, description="Average cost per task")

    available_quota: int = Field(0, ge=0, description="Available token quota")
    agent_pool_size: int = Field(0, ge=0, description="Total agent pool size")
    queue_capacity_percent: float = Field(
        0.0, ge=0, le=100, description="Queue capacity utilization"
    )
    resource_headroom_percent: float = Field(
        0.0, ge=0, le=100, description="Resource headroom percentage"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics timestamp"
    )

    def get_overall_health(self) -> EnumSystemHealth:
        """Calculate overall system health status."""
        if (
            self.api_availability >= 99.0
            and self.database_connectivity
            and self.aggregate_success_rate >= 95.0
            and self.resource_headroom_percent >= 20.0
        ):
            return EnumSystemHealth.HEALTHY
        elif (
            self.api_availability >= 90.0
            and self.database_connectivity
            and self.aggregate_success_rate >= 80.0
            and self.resource_headroom_percent >= 10.0
        ):
            return EnumSystemHealth.DEGRADED
        else:
            return EnumSystemHealth.CRITICAL
