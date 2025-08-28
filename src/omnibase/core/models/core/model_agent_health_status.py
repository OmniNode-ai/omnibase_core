"""
Model for agent system health status.

This model represents the health status of the agent manager service
and overall system health metrics.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class HealthStatusType(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ModelHealthCheck(BaseModel):
    """Individual health check result."""

    name: str = Field(description="Name of the health check")
    status: HealthStatusType = Field(description="Status of this health check")
    message: Optional[str] = Field(
        default=None, description="Health check message or error details"
    )
    response_time_ms: float = Field(description="Response time in milliseconds")
    last_checked: datetime = Field(
        default_factory=datetime.now, description="Timestamp of last check"
    )


class ModelSystemMetrics(BaseModel):
    """System-level metrics."""

    total_agents: int = Field(description="Total number of agent instances")
    active_agents: int = Field(description="Number of active agents")
    idle_agents: int = Field(description="Number of idle agents")
    working_agents: int = Field(description="Number of working agents")
    error_agents: int = Field(description="Number of agents in error state")
    system_cpu_percent: float = Field(description="System CPU usage percentage")
    system_memory_percent: float = Field(description="System memory usage percentage")
    system_disk_percent: float = Field(description="System disk usage percentage")
    event_bus_connected: bool = Field(description="Whether event bus is connected")
    api_quota_remaining: Optional[int] = Field(
        default=None, description="Remaining API quota"
    )
    api_requests_per_minute: float = Field(
        description="Current API requests per minute"
    )


class ModelAgentHealthStatus(BaseModel):
    """Complete agent system health status."""

    overall_status: HealthStatusType = Field(description="Overall system health status")
    health_checks: List[ModelHealthCheck] = Field(
        description="Individual health check results"
    )
    system_metrics: ModelSystemMetrics = Field(description="System-level metrics")
    service_uptime_seconds: int = Field(description="Service uptime in seconds")
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Health status last update timestamp"
    )
    alerts: List[str] = Field(default_factory=list, description="Current system alerts")

    @property
    def health_score(self) -> float:
        """Calculate overall health score from 0.0 to 1.0."""
        if not self.health_checks:
            return 0.0

        scores = {
            HealthStatusType.HEALTHY: 1.0,
            HealthStatusType.DEGRADED: 0.5,
            HealthStatusType.UNHEALTHY: 0.0,
            HealthStatusType.UNKNOWN: 0.0,
        }

        total_score = sum(scores[check.status] for check in self.health_checks)
        return total_score / len(self.health_checks)
