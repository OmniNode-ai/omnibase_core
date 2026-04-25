# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelInvocationCommand: reducer to dispatcher command envelope."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind
from omnibase_core.enums.enum_model_routing_backend import EnumModelRoutingBackend
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelInvocationCommand(BaseModel):
    """Typed command emitted by the routing reducer."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    task_id: UUID
    correlation_id: UUID
    invocation_kind: EnumInvocationKind
    agent_protocol: EnumAgentProtocol | None = None
    model_backend: EnumModelRoutingBackend | None = None
    target_ref: str = Field(min_length=1)
    payload: dict[str, ModelSchemaValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_axis_consistency(self) -> ModelInvocationCommand:
        """Ensure AGENT commands use protocol and MODEL commands use backend."""
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


__all__ = ["ModelInvocationCommand"]
