# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRemoteTaskState: persisted remote task state row."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_agent_task_lifecycle_type import (
    EnumAgentTaskLifecycleType,
)
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind


class ModelRemoteTaskState(BaseModel):
    """Persisted row used to resume unfinished remote tasks after restart."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    task_id: UUID
    invocation_kind: EnumInvocationKind
    protocol: EnumAgentProtocol | None = None
    target_ref: str = Field(min_length=1)
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
