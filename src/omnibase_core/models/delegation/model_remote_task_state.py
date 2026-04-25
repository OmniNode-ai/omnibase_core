# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelRemoteTaskState: durable state for restart-safe remote task resumption (OMN-9637)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_agent_task_lifecycle_type import (
    EnumAgentTaskLifecycleType,
)
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind


class ModelRemoteTaskState(BaseModel):
    """Persisted state for a remote agent task invocation.

    Rows are created and updated by node_remote_agent_invoke_effect.
    Used to resume unfinished remote tasks after service restart.
    """

    model_config = ConfigDict(frozen=True)

    task_id: UUID
    invocation_kind: EnumInvocationKind
    protocol: EnumAgentProtocol | None = None
    target_ref: str
    remote_task_handle: str | None = None
    correlation_id: UUID
    status: EnumAgentTaskLifecycleType
    last_remote_status: str | None = None
    last_emitted_event_type: EnumAgentTaskLifecycleType | None = None
    submitted_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


__all__ = ["ModelRemoteTaskState"]
