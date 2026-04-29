# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical host-local runtime skill request model."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.types import JsonType


class ModelRuntimeSkillRequest(BaseModel):
    """Typed request sent from a skill wrapper to the local runtime transport."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    command_name: str = Field(..., min_length=1, description="Logical command name.")
    payload: dict[str, JsonType] = Field(
        default_factory=dict,
        description="JSON payload forwarded to runtime execution.",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional caller-supplied correlation identifier.",
    )
    timeout_ms: int = Field(
        default=300_000,
        gt=0,
        le=900_000,
        description="Total request timeout for local runtime dispatch.",
    )

    @field_validator("command_name")
    @classmethod
    def _validate_command_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("command_name must be a non-empty string")
        return normalized


__all__ = ["ModelRuntimeSkillRequest"]
