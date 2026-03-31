# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Event headers model for the core in-memory event bus.

Lightweight version of the infra ModelEventHeaders with no
infrastructure-specific validators or dependencies.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelEventHeaders(BaseModel):
    """Headers for event bus messages.

    Carries tracing, routing, and retry metadata for event messages.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    content_type: str = Field(default="application/json")
    correlation_id: UUID = Field(default_factory=uuid4)
    message_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(
        ..., description="Message creation timestamp (must be explicitly provided)"
    )
    source: str
    event_type: str
    schema_version: str = Field(default="1.0.0")
    destination: str | None = Field(default=None)
    trace_id: str | None = Field(default=None)
    span_id: str | None = Field(default=None)
    parent_span_id: str | None = Field(default=None)
    operation_name: str | None = Field(default=None)
    priority: Literal["low", "normal", "high", "critical"] = Field(default="normal")
    routing_key: str | None = Field(default=None)
    partition_key: str | None = Field(default=None)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    ttl_seconds: int | None = Field(default=None)

    async def validate_headers(self) -> bool:
        """Validate that required headers are present and valid."""
        return bool(self.correlation_id and self.event_type)


__all__: list[str] = ["ModelEventHeaders"]
