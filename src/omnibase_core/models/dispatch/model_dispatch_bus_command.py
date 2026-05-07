# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pattern B broker command payload model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types import JsonType


class ModelDispatchBusCommand(BaseModel):
    """Command payload published to the Pattern B broker."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    command_name: str = Field(
        ...,
        min_length=1,
        description="Logical command name for the broker request.",
    )
    requester: str = Field(
        ...,
        min_length=1,
        description="Originating surface, e.g. codex or opencode.",
    )
    payload: JsonType = Field(
        ...,
        description="JSON-serializable broker command payload.",
    )
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Correlation identifier shared with the terminal result.",
    )
    response_topic: str = Field(
        ...,
        min_length=1,
        description="Terminal topic the broker should publish the result to.",
    )
    timeout_seconds: int = Field(
        default=120,
        ge=1,
        le=600,
        description="Requested timeout for the broker round-trip.",
    )
    target_runtime_address: str | None = Field(
        default=None,
        description="Optional runtime:// address selector for routed dispatch.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the broker request was created.",
    )


__all__ = ["ModelDispatchBusCommand"]
