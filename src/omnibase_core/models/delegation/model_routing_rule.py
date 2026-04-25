# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRoutingRule: declarative reducer routing rule."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind
from omnibase_core.enums.enum_model_routing_backend import EnumModelRoutingBackend


class ModelRoutingRule(BaseModel):
    """Capability to invocation-kind target mapping."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    capability: EnumAgentCapability
    invocation_kind: EnumInvocationKind
    agent_protocol: EnumAgentProtocol | None = None
    model_backend: EnumModelRoutingBackend | None = None
    target_ref: str = Field(min_length=1)
    fallbacks: tuple[str, ...] = Field(default=())

    @model_validator(mode="after")
    def validate_axis_consistency(self) -> ModelRoutingRule:
        """Ensure AGENT rules use protocol and MODEL rules use backend."""
        if self.invocation_kind is EnumInvocationKind.AGENT:
            if self.agent_protocol is None:
                raise ValueError("invocation_kind=AGENT requires agent_protocol")
            if self.model_backend is not None:
                raise ValueError("invocation_kind=AGENT forbids model_backend")
            return self

        if self.model_backend is None:
            raise ValueError("invocation_kind=MODEL requires model_backend")
        if self.agent_protocol is not None:
            raise ValueError("invocation_kind=MODEL forbids agent_protocol")
        return self


__all__ = ["ModelRoutingRule"]
