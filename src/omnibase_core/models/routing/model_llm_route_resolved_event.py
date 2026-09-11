# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelLlmRouteResolvedEvent: canonical event for resolved LLM routes."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.routing.model_served_model_ref import ModelServedModelRef


class ModelLlmRouteResolvedEvent(BaseModel):
    """Event emitted when model routing resolves to a concrete endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    routing_decision_id: UUID = Field(
        ..., description="Router-owned UUID generated once for this routing decision."
    )
    correlation_id: str = Field(..., description="Originating correlation id.")
    logical_model_key: str = Field(
        ..., description="Logical model key requested by policy."
    )
    served_model_id: ModelServedModelRef = Field(
        ..., description="Provider-qualified concrete model selected from the registry."
    )
    endpoint_ref: str = Field(
        ..., description="Contract-owned endpoint reference; never a secret value."
    )
    provider: str = Field(..., description="Provider that owns the served model.")
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
        description="Reason fallback was used; empty when primary route resolved.",
    )
    used_fallback: bool = Field(
        default=False, description="True when the resolved route used fallback."
    )
    created_at: datetime = Field(..., description="UTC event creation time.")

    @model_validator(mode="after")
    def _policy_hash_alias_matches(self) -> Self:
        if self.policy_hash != self.routing_policy_hash:
            msg = "policy_hash must equal routing_policy_hash"
            raise ValueError(msg)
        if self.served_model_id.provider != self.provider:
            msg = "served_model_id provider must equal event provider"
            raise ValueError(msg)
        return self


__all__ = ["ModelLlmRouteResolvedEvent"]
