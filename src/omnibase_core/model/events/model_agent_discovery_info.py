"""
Model for agent discovery information.

Provides strongly-typed structure for agent discovery data with proper ONEX compliance.
"""

from pydantic import BaseModel, Field


class ModelAgentDiscoveryInfo(BaseModel):
    """
    Agent discovery information.

    Replaces Dict[str, Any] usage for agent discovery data.
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_role: str = Field(..., description="Agent role/purpose")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Agent capabilities",
    )
    status: str = Field("unknown", description="Current agent status")
    device_id: str | None = Field(None, description="Device hosting the agent")
    endpoint: str | None = Field(None, description="Agent communication endpoint")
    last_seen: str | None = Field(None, description="Last seen timestamp")
    health_score: float | None = Field(
        None,
        description="Agent health score 0.0-1.0",
    )
