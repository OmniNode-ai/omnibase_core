# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Recorded timestamps for display only; never used as graph structure."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ModelExecutionGraphLabel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: UUID
    event_timestamp: datetime | None = None
    ledger_written_at: datetime | None = None
