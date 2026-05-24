# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRouteRequest — input DTO for node_model_router resolution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRouteRequest(BaseModel):
    """Request payload to resolve a logical model key to a concrete endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    logical_model_key: str = Field(
        ...,
        description="Logical model key to resolve (e.g. 'qwen3-coder-30b').",
    )
    role: str = Field(
        ...,
        description="Caller role (e.g. 'fixer', 'reviewer'). Used for fallback authorization.",
    )
    correlation_id: str = Field(
        ...,
        description="Correlation ID linking this request to the originating workflow.",
    )
    require_healthy: bool = Field(
        default=True,
        description="When True, router skips degraded endpoints and applies fallback policy.",
    )


__all__: list[str] = ["ModelRouteRequest"]
