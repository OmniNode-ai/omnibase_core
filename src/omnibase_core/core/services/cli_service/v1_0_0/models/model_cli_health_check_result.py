"""
CLI health check result model for ONEX CLI operations.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelCliHealthCheckResult(BaseModel):
    """Strongly typed health check result."""

    status: str = Field(...)
    node_name: str = Field(...)
    details: dict[str, str] = Field(default_factory=dict)
