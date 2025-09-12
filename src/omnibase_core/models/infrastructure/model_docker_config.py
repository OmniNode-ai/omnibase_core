"""
Docker configuration models.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DockerLogDriver(str, Enum):
    """Docker log driver options."""

    JSON_FILE = "json-file"
    SYSLOG = "syslog"
    JOURNALD = "journald"
    GELF = "gelf"


class DockerNetworkDriver(str, Enum):
    """Docker network driver options."""

    BRIDGE = "bridge"
    HOST = "host"
    OVERLAY = "overlay"
    MACVLAN = "macvlan"


class DockerRestartPolicy(str, Enum):
    """Docker restart policy options."""

    NO = "no"
    ALWAYS = "always"
    ON_FAILURE = "on-failure"
    UNLESS_STOPPED = "unless-stopped"


class ModelDockerBuildArg(BaseModel):
    """Docker build argument model."""

    name: str = Field(..., description="Build argument name")
    value: str = Field(..., description="Build argument value")


class ModelDockerBuildStage(BaseModel):
    """Docker build stage model."""

    name: str = Field(..., description="Build stage name")
    from_image: str = Field(..., description="Base image for this stage")
    commands: list[str] = Field(default_factory=list, description="Build commands")


class ModelDockerCompose(BaseModel):
    """Docker Compose configuration model."""

    version: str = Field("3.8", description="Docker Compose version")
    services: dict[str, Any] = Field(
        default_factory=dict, description="Services configuration"
    )
    networks: dict[str, Any] = Field(
        default_factory=dict, description="Networks configuration"
    )
    volumes: dict[str, Any] = Field(
        default_factory=dict, description="Volumes configuration"
    )


class ModelDockerContainer(BaseModel):
    """Docker container configuration model."""

    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Docker image")
    ports: list[str] = Field(default_factory=list, description="Port mappings")
    environment: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    restart_policy: DockerRestartPolicy = Field(
        DockerRestartPolicy.UNLESS_STOPPED, description="Restart policy"
    )


class ModelDockerNetwork(BaseModel):
    """Docker network configuration model."""

    name: str = Field(..., description="Network name")
    driver: DockerNetworkDriver = Field(
        DockerNetworkDriver.BRIDGE, description="Network driver"
    )
    options: dict[str, Any] = Field(default_factory=dict, description="Network options")


class ModelDockerVolume(BaseModel):
    """Docker volume configuration model."""

    name: str = Field(..., description="Volume name")
    driver: str = Field("local", description="Volume driver")
    options: dict[str, Any] = Field(default_factory=dict, description="Volume options")
