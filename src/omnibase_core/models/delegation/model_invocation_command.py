# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelInvocationCommand: typed command emitted by the routing reducer (OMN-9637)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

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


__all__ = ["ModelInvocationCommand"]
