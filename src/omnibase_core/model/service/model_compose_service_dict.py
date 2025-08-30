"""
Model for Docker Compose service dictionary representation.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ModelComposeServiceDict(BaseModel):
    """Dictionary representation of a compose service for YAML serialization."""

    image: Optional[str] = Field(default=None, description="Docker image")
    build: Optional[Dict[str, str]] = Field(
        default=None, description="Build configuration"
    )
    command: Optional[Union[str, List[str]]] = Field(
        default=None, description="Command to run"
    )
    environment: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables"
    )
    ports: Optional[List[str]] = Field(default=None, description="Port mappings")
    volumes: Optional[List[str]] = Field(default=None, description="Volume mounts")
    depends_on: Optional[Dict[str, Dict[str, str]]] = Field(
        default=None, description="Service dependencies"
    )
    healthcheck: Optional[Dict[str, Union[str, int, List[str]]]] = Field(
        default=None, description="Health check config"
    )
    restart: Optional[str] = Field(default=None, description="Restart policy")
    networks: Optional[List[str]] = Field(default=None, description="Networks to join")
    labels: Optional[Dict[str, str]] = Field(
        default=None, description="Container labels"
    )
    deploy: Optional[Dict[str, Dict[str, Union[str, int, Dict[str, str]]]]] = Field(
        default=None, description="Deploy config"
    )
