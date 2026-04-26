# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelInvocationCommand: typed command emitted by the routing reducer (OMN-9637)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelInvocationCommand(BaseModel):
    """Typed invocation command emitted by the delegation routing reducer.

    Carries all routing resolution outputs needed for the orchestrator FSM and
    the remote-agent invoke effect to act on the delegation request.
    """

    model_config = ConfigDict(frozen=True)

    task_id: UUID
    correlation_id: UUID
    invocation_kind: EnumInvocationKind
    agent_protocol: EnumAgentProtocol | None = None
    model_backend: str | None = None
    target_ref: str
    payload: dict[str, ModelSchemaValue] = {}

    @model_validator(mode="after")
    def _validate_kind_invariants(self) -> ModelInvocationCommand:
        if (
            self.invocation_kind is EnumInvocationKind.AGENT
            and self.agent_protocol is None
        ):
            msg = "agent_protocol is required when invocation_kind is AGENT"
            raise ValueError(msg)
        if (
            self.invocation_kind is EnumInvocationKind.AGENT
            and self.model_backend is not None
        ):
            msg = "model_backend must be None when invocation_kind is AGENT"
            raise ValueError(msg)
        if (
            self.invocation_kind is EnumInvocationKind.MODEL
            and self.model_backend is None
        ):
            msg = "model_backend is required when invocation_kind is MODEL"
            raise ValueError(msg)
        if (
            self.invocation_kind is EnumInvocationKind.MODEL
            and self.agent_protocol is not None
        ):
            msg = "agent_protocol must be None when invocation_kind is MODEL"
            raise ValueError(msg)
        return self


__all__ = ["ModelInvocationCommand"]
