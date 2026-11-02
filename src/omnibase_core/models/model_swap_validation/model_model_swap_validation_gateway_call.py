# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cost evidence for an individual forwarded model call."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_model_swap_cost_measurement_source import (
    EnumModelSwapCostMeasurementSource,
)
from omnibase_core.enums.enum_model_swap_gateway_role import EnumModelSwapGatewayRole


class ModelModelSwapValidationGatewayCall(BaseModel):
    """A call receipt that distinguishes provider charges from price estimates."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, allow_inf_nan=False
    )

    role: EnumModelSwapGatewayRole
    model_id: str = Field(min_length=1)
    tokens_in: int = Field(ge=0, strict=True)
    tokens_out: int = Field(ge=0, strict=True)
    cost_usd: float | None = Field(default=None, ge=0)
    cost_measurement_source: EnumModelSwapCostMeasurementSource

    @model_validator(mode="after")
    def validate_cost_provenance(self) -> ModelModelSwapValidationGatewayCall:
        """An unpriced call has no cost; a priced call must supply its cost."""
        unpriced = (
            self.cost_measurement_source == EnumModelSwapCostMeasurementSource.UNPRICED
        )
        if unpriced != (self.cost_usd is None):
            raise ValueError("cost_usd must be null exactly when the call is unpriced")
        return self


__all__ = ["ModelModelSwapValidationGatewayCall"]
