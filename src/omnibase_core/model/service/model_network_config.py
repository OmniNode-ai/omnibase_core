"""
Network configuration model for service deployment.
"""

from pydantic import BaseModel, Field


class ModelNetworkConfig(BaseModel):
    """Network configuration for service deployment."""

    port: int = Field(8080, description="Service port", ge=1024, le=65535)
    host: str = Field("0.0.0.0", description="Service host")
    expose_port: bool = Field(True, description="Expose port to host")
    network_name: str | None = Field(None, description="Docker network name")
