"""
Model for agent discovery information.

Provides strongly-typed structure for agent discovery data with proper ONEX compliance.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelAgentDiscoveryInfo(BaseModel):
    """
    Agent discovery information.

    Replaces Dict[str, Any] usage for agent discovery data.
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_role: str = Field(..., description="Agent role/purpose")
    capabilities: List[str] = Field(
        default_factory=list, description="Agent capabilities"
    )
    status: str = Field("unknown", description="Current agent status")
    device_id: Optional[str] = Field(None, description="Device hosting the agent")
    endpoint: Optional[str] = Field(None, description="Agent communication endpoint")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp")
    health_score: Optional[float] = Field(
        None, description="Agent health score 0.0-1.0"
    )
