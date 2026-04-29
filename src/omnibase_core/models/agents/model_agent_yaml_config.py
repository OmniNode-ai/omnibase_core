# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Top-level schema for agent YAML configuration files (plugins/onex/agents/configs/*.yaml)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.agents.model_agent_identity import ModelAgentIdentity
from omnibase_core.models.agents.model_agent_yaml_activation_patterns import (
    ModelActivationPatterns,
)


class ModelAgentConfig(BaseModel):
    """Top-level schema for an agent configuration YAML.

    Validates agent config files at plugins/onex/agents/configs/*.yaml.
    """

    model_config = ConfigDict(
        extra="ignore", populate_by_name=True, from_attributes=True
    )

    # string-version-ok: wire type read from YAML agent config files
    schema_version: str = Field(..., description="Schema version (semver)")
    agent_type: str = Field(..., description="Agent type identifier")
    agent_identity: ModelAgentIdentity = Field(..., description="Agent identity block")
    activation_patterns: ModelActivationPatterns = Field(
        ..., description="Activation trigger patterns"
    )
    disallowed_tools: list[str] = Field(
        default_factory=list,
        alias="disallowedTools",
        description="Tools this agent must not use",
    )


__all__ = ["ModelAgentConfig"]
