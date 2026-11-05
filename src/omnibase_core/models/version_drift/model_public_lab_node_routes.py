# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The shrink-only list of typed public lab routes (OMN-19998)."""

from __future__ import annotations

from collections import Counter
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.version_drift.model_public_lab_node_route import (
    ModelPublicLabNodeRoute,
)

__all__ = ["ModelPublicLabNodeRoutes"]


class ModelPublicLabNodeRoutes(BaseModel):
    """Every public-repository job still allowed to select the lab, by typed route.

    Attributes:
        routes: The routes; two routes for one job are refused.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    routes: tuple[ModelPublicLabNodeRoute, ...] = Field(default=())

    @model_validator(mode="after")
    def _one_route_per_job(self) -> Self:
        repeated = [k for k, n in Counter(r.key for r in self.routes).items() if n > 1]
        if repeated:
            raise ValueError(f"more than one route for {sorted(repeated)}")
        return self

    def keys(self) -> frozenset[tuple[str, str, str]]:
        """The job identities the list covers."""
        return frozenset(route.key for route in self.routes)
