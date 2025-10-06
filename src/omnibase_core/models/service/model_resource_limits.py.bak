from pydantic import Field

"""
Resource limits model for container deployment.
"""

from pydantic import BaseModel, Field


class ModelResourceLimits(BaseModel):
    """Resource limits for container deployment."""

    memory_mb: int | None = Field(None, description="Memory limit in MB", ge=64)
    cpu_cores: float | None = Field(None, description="CPU limit in cores", ge=0.1)
    storage_mb: int | None = Field(None, description="Storage limit in MB", ge=100)
