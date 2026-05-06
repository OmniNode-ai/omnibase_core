# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelModelHealthStatus: health snapshot for a model endpoint (OMN-10611)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_model_health_state import EnumModelHealthState


class ModelModelHealthStatus(BaseModel):
    """Point-in-time health snapshot for a model endpoint.

    Used by the delegation routing reducer to skip unavailable models.
    If all models are unavailable, the original Claude Code tool call proceeds.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    model_key: str
    endpoint_url: str
    state: EnumModelHealthState
    latency_ms: float | None = Field(default=None, ge=0)
    latency_threshold_ms: float = Field(default=5000.0, ge=0)
    last_checked_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    error_message: str | None = None
    consecutive_failures: int = Field(default=0, ge=0)


__all__ = ["ModelModelHealthStatus"]
