from pydantic import BaseModel, Field


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
    api_quota_remaining: int | None = Field(
        default=None,
        description="Remaining API quota",
    )
    api_requests_per_minute: float = Field(
        description="Current API requests per minute",
    )
