"""
Model for health status information.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_semver import ModelSemVer


class ModelToolHealthStatus(BaseModel):
    """Health status information for a tool."""

    status: str = Field(description="Health status (healthy/degraded)")
    timestamp: str = Field(description="Timestamp of health check")
    tool_name: str = Field(description="Name of the tool")
    version: ModelSemVer = Field(description="Version as SemVer")
    checks: dict[str, bool] = Field(description="Individual health check results")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00",
                "tool_name": "tool_example",
                "version": {
                    "major": 1,
                    "minor": 0,
                    "patch": 0,
                    "prerelease": None,
                    "build": None,
                },
                "checks": {
                    "contract_exists": True,
                    "models_valid": True,
                    "imports_resolvable": True,
                },
            },
        }
