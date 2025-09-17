"""
Model for health status information.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_semver import ModelSemVer


class ModelNodeHealthStatus(BaseModel):
    """Health status information for a node."""

    status: str = Field(description="Health status (healthy/degraded)")
    timestamp: str = Field(description="Timestamp of health check")
    node_name: str = Field(description="Name of the node")
    version: ModelSemVer = Field(description="Version as SemVer")
    checks: dict[str, bool] = Field(description="Individual health check results")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00",
                "node_name": "node_example",
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
