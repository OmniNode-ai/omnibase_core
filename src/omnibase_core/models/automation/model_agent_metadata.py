"""
Metadata model for agent allocations.

Provides strongly typed metadata structure for agents.
"""

from pydantic import BaseModel, Field


class ModelAgentMetadata(BaseModel):
    """Metadata for agent allocations."""

    spawn_reason: str = Field(
        default="scheduled",
        description="Reason for agent creation",
    )
    parent_agent_id: str | None = Field(
        None,
        description="Parent agent if spawned from recovery",
    )
    recovery_count: int = Field(default=0, description="Number of recovery attempts")
    performance_tier: str = Field(
        default="standard",
        description="Performance tier (standard, high, low)",
    )
    specialized_capabilities: list[str] = Field(
        default_factory=list,
        description="Special capabilities of this agent",
    )
    work_history: list[str] = Field(
        default_factory=list,
        description="Recent work item IDs",
    )
    notes: str | None = Field(None, description="Additional agent notes")
