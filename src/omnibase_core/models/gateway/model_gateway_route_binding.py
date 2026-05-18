# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGatewayRouteBinding — gateway route-to-contract binding model — OMN-11193."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelGatewayRouteBinding"]


class ModelGatewayRouteBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    path_pattern: str = Field(..., min_length=1)
    contract_id: str = Field(
        ...,
        min_length=1,
        description="Must resolve to a registered wire schema or command contract. NOT merely a topic string.",
    )
