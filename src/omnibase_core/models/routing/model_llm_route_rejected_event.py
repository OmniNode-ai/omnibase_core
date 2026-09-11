# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelLlmRouteRejectedEvent: canonical event for rejected LLM routes."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_routing_error_class import RoutingErrorClass
from omnibase_core.models.routing.model_served_model_ref import ModelServedModelRef


class ModelLlmRouteRejectedEvent(BaseModel):
    """Event emitted when model routing fails closed without a served endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    routing_decision_id: UUID = Field(
        ..., description="Router-owned UUID generated once for this routing decision."
    )
    correlation_id: str = Field(..., description="Originating correlation id.")
    logical_model_key: str = Field(
        ..., description="Logical model key requested by policy."
    )
    served_model_id: ModelServedModelRef | None = Field(
        default=None,
        description="Provider-qualified model reference when a model was attempted.",
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
        if (
            self.served_model_id is not None
            and self.served_model_id.provider != self.provider
        ):
            msg = "served_model_id provider must equal event provider"
            raise ValueError(msg)
        return self


__all__ = ["ModelLlmRouteRejectedEvent"]
