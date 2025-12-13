"""
Network configuration model for service deployment.
"""

from pydantic import BaseModel, Field


class ModelNetworkConfig(BaseModel):
    """Network configuration for service deployment."""

    port: int = Field(default=8080, description="Service port", ge=1024, le=65535)
    host: str = Field(
        default="0.0.0.0",
        description="Service host",
    )
    expose_port: bool = Field(default=True, description="Expose port to host")
    network_name: str | None = Field(default=None, description="Docker network name")
