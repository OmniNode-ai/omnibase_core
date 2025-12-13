"""Tool discovery result model with validation details."""

from pathlib import Path

from pydantic import BaseModel, Field

from omnibase_core.models.discovery.model_discovery_config import ModelDiscoveryConfig
from omnibase_core.models.discovery.model_tool_discovery_error import (
    ModelToolDiscoveryError,
)


class ModelToolDiscoveryResult(BaseModel):
    """Result of tool discovery with validation details."""

    discovered_tools: list[Path] = Field(
        default_factory=list,
        description="Successfully discovered tools",
    )
    invalid_tools: list[ModelToolDiscoveryError] = Field(
        default_factory=list,
        description="Tools with invalid contracts",
    )
    skipped_tools: list[ModelToolDiscoveryError] = Field(
        default_factory=list,
        description="Tools skipped for other reasons",
    )
    total_discovered: int = Field(
        default=0,
        description="Total number of valid tools discovered",
        ge=0,
    )
    discovery_config: ModelDiscoveryConfig = Field(
        default=...,
        description="Discovery configuration used",
    )
