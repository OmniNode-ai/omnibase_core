# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelProjectionDegradedEvent — projection SLA breach event model — OMN-11193."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelProjectionDegradedEvent"]


class ModelProjectionDegradedEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    projection_name: str
    sla_seconds: int
    actual_staleness_seconds: float
    degraded_behavior: str
    observed_at: datetime
    source_contract_hash: str
