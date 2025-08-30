"""
Model for production snapshot.

Complete production monitoring snapshot.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.monitoring.enum_agent_state import EnumAgentState
from omnibase_core.model.monitoring.model_agent_health_metrics import \
    ModelAgentHealthMetrics
from omnibase_core.model.monitoring.model_business_metrics import \
    ModelBusinessMetrics
from omnibase_core.model.monitoring.model_service_dependency import \
    ModelServiceDependency
from omnibase_core.model.monitoring.model_system_health_metrics import \
    ModelSystemHealthMetrics


class ModelProductionSnapshot(BaseModel):
    """Complete production monitoring snapshot."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Snapshot timestamp"
    )

    system_health: ModelSystemHealthMetrics = Field(
        ..., description="System health metrics"
    )
    business_metrics: ModelBusinessMetrics = Field(..., description="Business KPIs")

    agent_metrics: List[ModelAgentHealthMetrics] = Field(
        default_factory=list, description="Individual agent metrics"
    )

    service_dependencies: List[ModelServiceDependency] = Field(
        default_factory=list, description="Service dependency statuses"
    )

    current_window: Optional[str] = Field(
        None, description="Current operational window"
    )
    next_transition: Optional[datetime] = Field(
        None, description="Next window transition"
    )

    alerts_active: int = Field(0, ge=0, description="Number of active alerts")
    incidents_open: int = Field(0, ge=0, description="Number of open incidents")

    def get_active_agents(self) -> int:
        """Get count of active agents."""
        return len(
            [
                agent
                for agent in self.agent_metrics
                if agent.status in [EnumAgentState.RUNNING, EnumAgentState.IDLE]
            ]
        )

    def get_failed_agents(self) -> int:
        """Get count of failed agents."""
        return len(
            [
                agent
                for agent in self.agent_metrics
                if agent.status == EnumAgentState.FAILED
            ]
        )

    def get_total_queue_depth(self) -> int:
        """Get total queue depth across all agents."""
        return sum(agent.queue_depth for agent in self.agent_metrics)

    def calculate_system_efficiency(self) -> float:
        """Calculate overall system efficiency."""
        if not self.agent_metrics:
            return 0.0

        total_efficiency = sum(agent.efficiency_score for agent in self.agent_metrics)
        return total_efficiency / len(self.agent_metrics)
