# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelA2ATaskResponse: wire model for A2A task submission/poll response (OMN-9637)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_agent_task_lifecycle_type import (
    EnumAgentTaskLifecycleType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelA2ATaskResponse(BaseModel):
    """Response from an A2A peer's task submission or poll endpoint."""

    model_config = ConfigDict(frozen=True)

    remote_task_handle: str
    status: EnumAgentTaskLifecycleType
    artifacts: list[dict[str, ModelSchemaValue]] = []
    error: str | None = None


__all__ = ["ModelA2ATaskResponse"]
