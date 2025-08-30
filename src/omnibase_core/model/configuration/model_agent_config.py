"""
Model for Claude Code agent configuration.

This model defines the configuration structure for Claude Code agents,
including authentication, permissions, environment settings, and safety parameters.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelAgentPermissions(BaseModel):
    """Agent permission configuration."""

    tools: Dict[str, bool] = Field(
        description="Tool access permissions (tool_name -> enabled)"
    )
    file_system: Dict[str, List[str]] = Field(
        description="File system access permissions (read/write/execute -> paths)"
    )
    git: Dict[str, bool] = Field(description="Git operation permissions")
    event_bus: Dict[str, List[str]] = Field(
        description="Event bus permissions (publish/subscribe -> event_types)"
    )


class ModelAgentSafety(BaseModel):
    """Agent safety configuration."""

    max_file_changes: int = Field(
        description="Maximum number of files that can be modified in one operation"
    )
    max_execution_time: int = Field(description="Maximum execution time in seconds")
    require_tests: bool = Field(
        description="Whether tests are required for code changes"
    )
    auto_rollback: bool = Field(
        description="Whether to automatically rollback failed operations"
    )
    validation_timeout: int = Field(
        description="Timeout for validation operations in seconds"
    )


class ModelAgentOnexSettings(BaseModel):
    """ONEX-specific agent settings."""

    enforce_naming_conventions: bool = Field(
        description="Whether to enforce ONEX naming conventions"
    )
    enforce_strong_typing: bool = Field(
        description="Whether to enforce strong typing (no Any)"
    )
    require_contract_compliance: bool = Field(
        description="Whether to require contract compliance"
    )
    generate_documentation: bool = Field(
        description="Whether to automatically generate documentation"
    )
    validate_imports: bool = Field(description="Whether to validate import structure")


class ModelAgentConfig(BaseModel):
    """Complete agent configuration."""

    agent_id: str = Field(description="Unique identifier for the agent")
    model: str = Field(
        default="claude-3-sonnet-20240229",
        description="Claude model to use for the agent",
    )
    api_key: str = Field(description="Anthropic API key for authentication")
    permissions: ModelAgentPermissions = Field(
        description="Agent permission configuration"
    )
    working_directory: str = Field(description="Working directory for agent operations")
    environment_vars: Dict[str, str] = Field(
        description="Environment variables for the agent"
    )
    safety: ModelAgentSafety = Field(description="Safety configuration for the agent")
    onex: ModelAgentOnexSettings = Field(description="ONEX-specific settings")
    hooks: Optional[Dict[str, str]] = Field(
        default=None, description="Hook scripts for agent lifecycle events"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Configuration creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Configuration last update timestamp"
    )
