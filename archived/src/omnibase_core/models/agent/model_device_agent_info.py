"""
Model for device-specific agent information.

Provides strongly-typed structure for tracking agents by device
with proper ONEX compliance.
"""

from pydantic import BaseModel, Field


class ModelDeviceAgentInfo(BaseModel):
    """Agent information for a specific device."""

    count: int = Field(0, description="Number of agents on this device")
    agents: list[str] = Field(default_factory=list, description="List of agent IDs")
