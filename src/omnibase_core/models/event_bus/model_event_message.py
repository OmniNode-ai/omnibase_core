# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Event message model for the core in-memory event bus."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_bus.model_event_headers import ModelEventHeaders


class ModelEventMessage(BaseModel):
    """Event bus message with topic, key, value, headers, and offset tracking."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", arbitrary_types_allowed=True, from_attributes=True
    )

    topic: str
    key: bytes | None = Field(default=None)
    value: bytes
    headers: ModelEventHeaders
    offset: str | None = Field(default=None)
    partition: int | None = Field(default=None)

    async def ack(self) -> None:
        """Acknowledge message processing (no-op for in-memory)."""
        return


__all__: list[str] = ["ModelEventMessage"]
