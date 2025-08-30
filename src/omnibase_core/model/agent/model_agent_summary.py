"""
Model for agent orchestrator summary data.

Provides strongly-typed structure for agent health, status, and task information
with proper ONEX compliance.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.agent.model_agent_health_summary import ModelAgentHealthSummary
from omnibase_core.model.agent.model_device_agent_info import ModelDeviceAgentInfo
from omnibase_core.model.agent.model_role_agent_info import ModelRoleAgentInfo


class ModelAgentSummary(BaseModel):
    """
    Summary of all agents and their status in the distributed orchestrator.

    Replaces Dict[str, Any] usage with strongly typed model structure
    for ONEX compliance.
    """

    total_agents: int = Field(0, description="Total number of active agents")
    by_device: dict[str, ModelDeviceAgentInfo] = Field(
        default_factory=dict,
        description="Agent breakdown by device identifier",
    )
    by_role: dict[str, ModelRoleAgentInfo] = Field(
        default_factory=dict,
        description="Agent breakdown by role/capability",
    )
    health_summary: ModelAgentHealthSummary = Field(
        default_factory=ModelAgentHealthSummary,
        description="Health status breakdown of all agents",
    )
    queued_tasks: int = Field(0, description="Number of tasks waiting in queue")
