"""Model for tracking agent health status."""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_device_type import EnumAgentHealth


class ModelAgentHealthMap(BaseModel):
    """
    Strongly-typed mapping of agent IDs to health status.

    Replaces Dict[str, EnumAgentHealth] to comply with ONEX
    standards requiring specific typed models.
    """

    health_status: dict[str, EnumAgentHealth] = Field(
        default_factory=dict,
        description="Map of agent IDs to health status",
    )

    last_updated: dict[str, datetime] = Field(
        default_factory=dict,
        description="Map of agent IDs to last health update time",
    )

    def update_health(self, agent_id: str, health: EnumAgentHealth) -> None:
        """Update health status for an agent."""
        self.health_status[agent_id] = health
        self.last_updated[agent_id] = datetime.utcnow()

    def get_health(self, agent_id: str) -> EnumAgentHealth | None:
        """Get health status for a specific agent."""
        return self.health_status.get(agent_id)

    def get_last_update(self, agent_id: str) -> datetime | None:
        """Get last update time for agent health."""
        return self.last_updated.get(agent_id)

    def remove_agent(self, agent_id: str) -> bool:
        """Remove health tracking for an agent."""
        if agent_id in self.health_status:
            del self.health_status[agent_id]
            if agent_id in self.last_updated:
                del self.last_updated[agent_id]
            return True
        return False

    def get_agents_by_health(self, health: EnumAgentHealth) -> list[str]:
        """Get all agent IDs with a specific health status."""
        return [
            agent_id
            for agent_id, status in self.health_status.items()
            if status == health
        ]

    def get_healthy_agents(self) -> list[str]:
        """Get all healthy agent IDs."""
        return self.get_agents_by_health(EnumAgentHealth.HEALTHY)

    def get_unhealthy_agents(self) -> list[str]:
        """Get all unhealthy agent IDs."""
        unhealthy_statuses = [
            EnumAgentHealth.DEGRADED,
            EnumAgentHealth.UNHEALTHY,
            EnumAgentHealth.CRITICAL,
        ]
        agents = []
        for status in unhealthy_statuses:
            agents.extend(self.get_agents_by_health(status))
        return agents

    def count_by_health(self, health: EnumAgentHealth | None = None) -> int:
        """Count agents by health status."""
        if health:
            return len(self.get_agents_by_health(health))
        return len(self.health_status)

    def get_health_summary(self) -> dict[EnumAgentHealth, int]:
        """Get summary of agent counts by health status."""
        summary = {}
        for health in EnumAgentHealth:
            count = len(self.get_agents_by_health(health))
            if count > 0:
                summary[health] = count
        return summary

    def clear(self) -> None:
        """Clear all health tracking."""
        self.health_status.clear()
        self.last_updated.clear()

    def is_stale(self, agent_id: str, max_age_seconds: int = 300) -> bool:
        """Check if health data is stale (older than max_age_seconds)."""
        last_update = self.get_last_update(agent_id)
        if not last_update:
            return True
        age = (datetime.utcnow() - last_update).total_seconds()
        return age > max_age_seconds
