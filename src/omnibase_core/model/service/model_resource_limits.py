"""
Resource limits model for container deployment.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelResourceLimits(BaseModel):
    """Resource limits for container deployment."""

    memory_mb: Optional[int] = Field(None, description="Memory limit in MB", ge=64)
    cpu_cores: Optional[float] = Field(None, description="CPU limit in cores", ge=0.1)
    storage_mb: Optional[int] = Field(None, description="Storage limit in MB", ge=100)
