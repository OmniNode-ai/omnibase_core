"""
Model for health status information.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelToolHealthStatus(BaseModel):
    """Health status information for a tool."""

    status: str = Field(description="Health status (healthy/degraded)")
    timestamp: str = Field(description="Timestamp of health check")
    tool_name: str = Field(description="Name of the tool")
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version as SemVer",
    )
    checks: dict[str, bool] = Field(description="Individual health check results")
