# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelTargetAgent: remote agent endpoint descriptor."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol


class ModelTargetAgent(BaseModel):
    """Endpoint descriptor resolved from ModelRoutingRule.target_ref."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    agent_ref: str = Field(min_length=1)
    protocol: EnumAgentProtocol
    base_url: str = Field(min_length=1)
    protocol_version: str = Field(min_length=1)


__all__ = ["ModelTargetAgent"]
