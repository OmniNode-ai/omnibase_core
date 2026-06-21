# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelProjectionRow: a materialized harness projection row (OMN-13420)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelProjectionRow(BaseModel):
    """A single materialized projection row written by a harness REDUCER handler."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(
        ..., description="Correlation ID linking the row to the originating command."
    )
    workflow: str = Field(
        ..., description="Harness workflow that produced the row (delegation | sea)."
    )
    terminal_topic: str = Field(
        ..., description="Topic of the terminal event that produced this projection."
    )
    status: str = Field(..., description="Terminal status (success | failure).")
    payload: dict[str, object] = Field(  # dict-str-any-ok: projection payload is JSON
        default_factory=dict,
        description="JSON-serializable terminal payload snapshot.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Row creation timestamp (UTC).",
    )


__all__ = ["ModelProjectionRow"]
