# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelLlmRouteRejectedEvent: canonical event for rejected LLM routes."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_routing_error_class import RoutingErrorClass


class ModelLlmRouteRejectedEvent(BaseModel):
    """Event emitted when model routing fails closed without a served endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    routing_decision_id: str = Field(
        ..., description="Stable identifier for this routing decision."
    )
    correlation_id: str = Field(..., description="Originating correlation id.")
    logical_model_key: str = Field(
        ..., description="Logical model key requested by policy."
    )
    served_model_id: str = Field(
        default="",
        description="Concrete model id if any model was attempted.",
    )
    endpoint_ref: str = Field(
        default="",
        description="Contract-owned endpoint reference if one was selected.",
    )
    provider: str = Field(default="", description="Provider if one was selected.")
    registry_hash: str = Field(
        ..., description="Hash of the model registry used for the decision."
    )
    routing_policy_hash: str = Field(
        ..., description="Hash of the routing policy used for the decision."
    )
    policy_hash: str = Field(
        ..., description="Alias for routing_policy_hash for consumers."
    )
    pricing_manifest_hash: str = Field(
        ..., description="Hash of pricing manifest used for cost provenance."
    )
    fallback_reason: str = Field(
        default="",
        description="Fallback reason from policy or terminal rejection reason.",
    )
    failure_class: RoutingErrorClass = Field(
        ..., description="Structured route rejection classification."
    )
    failure_reason: str = Field(
        ..., description="Human-readable route rejection reason."
    )
    created_at: datetime = Field(..., description="UTC event creation time.")

    @model_validator(mode="after")
    def _policy_hash_alias_matches(self) -> Self:
        if self.policy_hash != self.routing_policy_hash:
            msg = "policy_hash must equal routing_policy_hash"
            raise ValueError(msg)
        return self


__all__ = ["ModelLlmRouteRejectedEvent"]
