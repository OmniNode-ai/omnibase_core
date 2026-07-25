# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Declared demand source for one demand-aware liveness surface.

OMN-15126 implementation of the OMN-14845 design (design §4).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDemandSourceRef"]


class ModelDemandSourceRef(BaseModel):
    """Declared source of eligible demand for one liveness surface (design §4)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["kafka_topic", "table_query", "scheduled_trigger", "webhook"]
    locator: str = Field(
        ..., min_length=1, description="Topic name / SQL locator / cron expression."
    )
    eligibility_predicate: str = Field(
        ..., min_length=1, description="Declared filter, e.g. 'state IN (...)'."
    )
