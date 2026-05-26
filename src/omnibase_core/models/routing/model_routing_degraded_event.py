# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRoutingDegradedEvent — emitted when the router flips to fallback."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRoutingDegradedEvent(BaseModel):
    """Event emitted on topic onex.evt.omnimarket.model-routing.degraded.v1.

    Published when consecutive failure streak cap is reached for a
    (endpoint, contract) pair and the router falls back to the secondary model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    primary: str = Field(..., description="model_id of the degraded primary endpoint.")
    reason: str = Field(..., description="Human-readable reason for degradation.")
    attempts: int = Field(
        ..., description="Number of consecutive failed attempts.", ge=1
    )
    elapsed_ms: float = Field(
        ..., description="Wall-clock elapsed time in milliseconds.", ge=0
    )
    merge_sha: str = Field(
        default="", description="Git SHA at time of event (if available)."
    )
    gate_name: str = Field(
        default="", description="Gate or handler name that triggered routing."
    )
    model_key: str = Field(..., description="Registry model_id key that degraded.")
    correlation_id: str = Field(
        ..., description="Correlation ID from the originating request."
    )


__all__: list[str] = ["ModelRoutingDegradedEvent"]
