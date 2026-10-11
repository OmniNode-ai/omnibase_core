# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aggregated result of the boundary parity handler."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.boundary_parity.model_boundary_parity_result import (
    ModelBoundaryParityResult,
)
from omnibase_core.models.nodes.boundary_parity.model_kafka_boundary_entry import (
    ModelKafkaBoundaryEntry,
)

__all__ = ["ModelBoundaryParityReport"]


class ModelBoundaryParityReport(BaseModel):
    """One result per checked boundary, plus the pending entries still in grace."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    results: list[ModelBoundaryParityResult] = Field(default_factory=list)
    pending_in_grace: list[ModelKafkaBoundaryEntry] = Field(default_factory=list)

    @property
    def has_mismatches(self) -> bool:
        """True when any boundary's producer or consumer misses its topic."""
        return any(not r.producer_ok or not r.consumer_ok for r in self.results)

    @property
    def mismatch_count(self) -> int:
        """Number of boundaries whose producer or consumer misses its topic."""
        return sum(1 for r in self.results if not r.producer_ok or not r.consumer_ok)
