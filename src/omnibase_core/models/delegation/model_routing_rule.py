# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelRoutingRule: delegation routing rule from contract.yaml (OMN-9637)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind


class ModelRoutingRule(BaseModel):
    """A single routing rule from the delegation reducer contract.

    Maps a capability to an invocation kind, protocol, and target reference.
    """

    model_config = ConfigDict(frozen=True)

    capability: EnumAgentCapability
    invocation_kind: EnumInvocationKind
    agent_protocol: EnumAgentProtocol | None = None
    model_backend: str | None = None
    target_ref: str
    fallbacks: tuple[str, ...] = ()


__all__ = ["ModelRoutingRule"]
