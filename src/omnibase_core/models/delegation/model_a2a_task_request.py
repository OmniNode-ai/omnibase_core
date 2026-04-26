# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelA2ATaskRequest: wire model for submitting a task via the A2A protocol (OMN-9637)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelA2ATaskRequest(BaseModel):
    """Request payload for submitting a task to a remote A2A peer."""

    model_config = ConfigDict(frozen=True)

    skill_ref: str
    input: dict[str, ModelSchemaValue]
    correlation_id: UUID


__all__ = ["ModelA2ATaskRequest"]
