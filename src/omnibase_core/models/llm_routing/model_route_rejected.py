# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRouteRejected — emitted when model key resolution fails."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.llm_routing.enum_route_rejection_reason import (
    EnumRouteRejectionReason,
)


class ModelRouteRejected(BaseModel):
    """Event payload for onex.evt.omnimarket.model-route-rejected.v1.

    Emitted when a logical model key cannot be resolved to a concrete
    endpoint due to an UNKNOWN_KEY, ENDPOINT_UNAVAILABLE, POLICY_REJECTED,
    or FALLBACK_EXHAUSTED condition.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    logical_model_key: str = Field(
        ...,
        description="The logical model key that failed resolution.",
    )
    rejection_reason: EnumRouteRejectionReason = Field(
        ...,
        description="Structured reason code for rejection.",
    )
    detail: str = Field(
        default="",
        description="Human-readable explanation for the rejection.",
    )
    correlation_id: str = Field(
        ...,
        description="Correlation ID from the originating route request.",
    )
    attempts: int = Field(
        default=1,
        description="Number of resolution attempts made (including fallback).",
        ge=1,
    )


__all__: list[str] = ["ModelRouteRejected"]
