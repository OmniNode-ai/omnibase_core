"""
Model for Docker network configuration.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelDockerNetworkConfig(BaseModel):
    """Docker network configuration for compose."""

    driver: str = Field(default="bridge", description="Network driver")
    driver_opts: Optional[Dict[str, str]] = Field(
        default=None, description="Driver options"
    )
    external: Optional[bool] = Field(default=False, description="External network")
    name: Optional[str] = Field(default=None, description="Network name")
