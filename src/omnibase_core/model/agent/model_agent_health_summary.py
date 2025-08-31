"""
Model for agent health summary statistics.

Provides strongly-typed structure for agent health breakdown
with proper ONEX compliance.
"""

from pydantic import BaseModel, Field


class ModelAgentHealthSummary(BaseModel):
    """Health summary statistics for all agents."""

    healthy: int = Field(0, description="Number of healthy agents")
    degraded: int = Field(0, description="Number of degraded agents")
    unhealthy: int = Field(0, description="Number of unhealthy agents")
