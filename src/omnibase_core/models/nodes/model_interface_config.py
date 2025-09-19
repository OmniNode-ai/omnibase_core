"""
Interface configuration model for EFFECT nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumAuthenticationMethod, EnumInterfaceProtocol


class ModelInterfaceConfig(BaseModel):
    """Interface configuration for EFFECT nodes."""

    model_config = ConfigDict(extra="forbid")

    protocol: EnumInterfaceProtocol = Field(
        ...,
        description="Interface protocol for communication",
    )
    host: str | None = Field(
        None,
        description="Interface host",
    )
    port: int | None = Field(
        None,
        description="Interface port",
        ge=1,
        le=65535,
    )
    ssl_enabled: bool = Field(
        default=False,
        description="Whether SSL is enabled",
    )
    authentication: EnumAuthenticationMethod | None = Field(
        None,
        description="Authentication method",
    )
