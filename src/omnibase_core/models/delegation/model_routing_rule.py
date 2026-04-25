# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelRoutingRule: delegation routing rule from contract.yaml (OMN-9637)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind


class ModelRoutingRule(BaseModel):
    """A single routing rule from the delegation reducer contract.

    Maps a capability to an invocation kind, protocol, and target reference.
    AGENT rules require agent_protocol; MODEL rules require model_backend.
    """

    model_config = ConfigDict(frozen=True)

    capability: EnumAgentCapability
    invocation_kind: EnumInvocationKind
    agent_protocol: EnumAgentProtocol | None = None
    model_backend: str | None = None
    target_ref: str
    fallbacks: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_protocol_for_kind(self) -> ModelRoutingRule:
        if (
            self.invocation_kind is EnumInvocationKind.AGENT
            and self.agent_protocol is None
        ):
            msg = "agent_protocol is required when invocation_kind is AGENT"
            raise ValueError(msg)
        if (
            self.invocation_kind is EnumInvocationKind.MODEL
            and self.model_backend is None
        ):
            msg = "model_backend is required when invocation_kind is MODEL"
            raise ValueError(msg)
        return self


__all__ = ["ModelRoutingRule"]
