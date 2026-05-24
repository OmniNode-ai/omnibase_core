# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelLlmRouteResolvedEvent: canonical event for resolved LLM routes."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelLlmRouteResolvedEvent(BaseModel):
    """Event emitted when model routing resolves to a concrete endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    routing_decision_id: str = Field(
        ..., description="Stable identifier for this routing decision."
    )
    correlation_id: str = Field(..., description="Originating correlation id.")
    logical_model_key: str = Field(
        ..., description="Logical model key requested by policy."
    )
    served_model_id: str = Field(
        ..., description="Concrete served model id selected from the registry."
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
        return self


__all__ = ["ModelLlmRouteResolvedEvent"]
