# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed provider-qualified identity for a model served by a router."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.routing.model_served_model_name import ModelServedModelName


class ModelServedModelRef(BaseModel):
    """Identifies the provider and concrete model selected by a route."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    provider: str = Field(..., description="Provider that served the model.")
    model_id: ModelServedModelName = Field(
        ..., description="Provider-local served model identifier."
    )

    @field_validator("provider")
    @classmethod
    def _require_nonempty_identifier(cls, value: str) -> str:
        """Reject empty or whitespace-only provider and model identifiers."""
        if not value.strip():
            msg = "served-model reference identifiers must be nonempty"
            raise ValueError(msg)
        return value


__all__ = ["ModelServedModelRef"]
