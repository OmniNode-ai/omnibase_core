# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pattern B broker terminal result payload model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types import JsonType


class ModelDispatchBusTerminalResult(BaseModel):
    """Terminal result returned by the Pattern B broker."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(
        ...,
        description="Correlation identifier copied from the originating request.",
    )
    status: Literal["completed", "failed", "timeout"] = Field(
        ...,
        description="Terminal broker request state.",
    )
    payload: JsonType | None = Field(
        default=None,
        description="JSON-serializable terminal payload when the broker succeeds.",
    )
    error_message: str | None = Field(
        default=None,
        description="Failure or timeout message when the broker does not complete cleanly.",
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the terminal result was created.",
    )


__all__ = ["ModelDispatchBusTerminalResult"]
