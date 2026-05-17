# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelProjectionRecoveredEvent — projection SLA recovery event model — OMN-11193."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelProjectionRecoveredEvent"]


class ModelProjectionRecoveredEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    projection_name: str
    recovered_at: datetime
    recovery_staleness_seconds: float
    source_contract_hash: str
