"""
Model for Docker build configuration.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelDockerBuildConfig(BaseModel):
    """Docker build configuration for compose services."""

    context: str = Field(default=".", description="Build context path")
    dockerfile: str = Field(default="Dockerfile", description="Path to Dockerfile")
    args: Optional[Dict[str, str]] = Field(default=None, description="Build arguments")
    target: Optional[str] = Field(default=None, description="Build target stage")
    cache_from: Optional[List[str]] = Field(
        default=None, description="Images to use as cache sources"
    )
    labels: Optional[Dict[str, str]] = Field(default=None, description="Build labels")
