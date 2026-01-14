from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.models.core.model_health_check_result import ModelHealthCheckResult
from omnibase_core.models.core.model_system_metrics import ModelSystemMetrics


class ModelAgentHealthStatus(BaseModel):
    """Complete agent system health status."""

    overall_status: EnumHealthStatus = Field(description="Overall system health status")
    health_checks: list[ModelHealthCheckResult] = Field(
        description="Individual health check results",
    )
    system_metrics: ModelSystemMetrics = Field(description="System-level metrics")
    service_uptime_seconds: int = Field(description="Service uptime in seconds")
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Health status last update timestamp",
    )
    alerts: list[str] = Field(default_factory=list, description="Current system alerts")

    @property
    def health_score(self) -> float:
        """Calculate overall health score from 0.0 to 1.0."""
        if not self.health_checks:
            return 0.0

        scores = {
            "healthy": 1.0,
            "degraded": 0.5,
            "unhealthy": 0.0,
            "unknown": 0.0,
        }

        # ModelHealthCheckResult.status is a string, so we use lowercase comparison
        total_score = sum(
            scores.get(check.status.lower(), 0.0) for check in self.health_checks
        )
        return total_score / len(self.health_checks)
