"""
Model for role-specific agent information.

Provides strongly-typed structure for tracking agents by role
with proper ONEX compliance.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelRoleAgentInfo(BaseModel):
    """Agent information for a specific role."""

    count: int = Field(0, description="Number of agents with this role")
    agents: List[str] = Field(default_factory=list, description="List of agent IDs")
