# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelAgentTaskLifecycleEvent: remote-agent task lifecycle event (OMN-9637)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_agent_task_lifecycle_type import (
    EnumAgentTaskLifecycleType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelAgentTaskLifecycleEvent(BaseModel):
    """Lifecycle event emitted by the remote-agent invoke effect.

    Emitted when the A2A transport reports a state transition on a remote task.
    """

    model_config = ConfigDict(frozen=True)

    task_id: UUID
    correlation_id: UUID
    lifecycle_type: EnumAgentTaskLifecycleType
    remote_task_handle: str | None = None
    artifact: dict[str, ModelSchemaValue] | None = None
    occurred_at: datetime
    remote_status: str | None = None
    error: str | None = None


__all__ = ["ModelAgentTaskLifecycleEvent"]
