"""
Model for Docker volume configuration.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelDockerVolumeConfig(BaseModel):
    """Docker volume configuration for compose."""

    driver: Optional[str] = Field(default=None, description="Volume driver")
    driver_opts: Optional[Dict[str, str]] = Field(
        default=None, description="Driver options"
    )
    external: Optional[bool] = Field(default=False, description="External volume")
    name: Optional[str] = Field(default=None, description="Volume name")
