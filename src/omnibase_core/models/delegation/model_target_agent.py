# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelTargetAgent: descriptor for a remote agent peer (OMN-9637)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol


class ModelTargetAgent(BaseModel):
    """Descriptor for a remote agent that can be invoked via a delegation protocol."""

    model_config = ConfigDict(frozen=True)

    target_ref: str
    base_url: str
    protocol: EnumAgentProtocol


__all__ = ["ModelTargetAgent"]
