from pydantic import Field

"""
Network configuration model for service deployment.
"""

from pydantic import BaseModel


class ModelNetworkConfig(BaseModel):
    """Network configuration for service deployment."""

    port: int = Field(default=8080, description="Service port", ge=1024, le=65535)
    host: str = Field(
        default="0.0.0.0", description="Service host"
    )  # noqa: S104 - Legitimate container service default binding to all interfaces
    expose_port: bool = Field(default=True, description="Expose port to host")
    network_name: str | None = Field(default=None, description="Docker network name")
