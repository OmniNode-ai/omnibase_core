# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed dollar cost for the Shared Experiment Result Contract (OMN-13613).

``cost_usd`` is a :class:`~decimal.Decimal` to avoid binary-float rounding drift
in cost accounting and aggregation across the three Phase-3 experiment
orchestrators of the SEA→canonical migration (epic OMN-13604).

.. versionadded:: OMN-13613
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelExperimentCost"]


class ModelExperimentCost(BaseModel):
    """Typed dollar cost for an experiment result."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    cost_usd: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Total experiment cost in US dollars (Decimal, never negative).",
    )
