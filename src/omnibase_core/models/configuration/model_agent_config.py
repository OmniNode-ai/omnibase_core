"""
Model for Claude Code agent configuration.

This model defines the configuration structure for Claude Code agents,
including authentication, permissions, environment settings, and safety parameters.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_agent_onex_settings import (
    ModelAgentOnexSettings,
)
from omnibase_core.models.configuration.model_agent_permissions import (
    ModelAgentPermissions,
)
from omnibase_core.models.configuration.model_agent_safety import ModelAgentSafety


class ModelAgentConfig(BaseModel):
    """Complete agent configuration."""

    agent_id: UUID = Field(description="Unique identifier for the agent")
    model: str = Field(
        default="claude-3-sonnet-20240229",
        description="Claude model to use for the agent",
    )
    api_key: str = Field(description="Anthropic API key for authentication")
    permissions: ModelAgentPermissions = Field(
        description="Agent permission configuration",
    )
    working_directory: str = Field(description="Working directory for agent operations")
    environment_vars: dict[str, str] = Field(
        description="Environment variables for the agent",
    )
    safety: ModelAgentSafety = Field(description="Safety configuration for the agent")
    onex: ModelAgentOnexSettings = Field(description="ONEX-specific settings")
    hooks: dict[str, str] | None = Field(
        default=None,
        description="Hook scripts for agent lifecycle events",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Configuration creation timestamp",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Configuration last update timestamp",
    )
