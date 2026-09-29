# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One row of the work-ledger projection snapshot (OMN-20002)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelWorkLedgerProjectionRow"]


class ModelWorkLedgerProjectionRow(BaseModel):
    """A confirmed event: its id, and the canonical JSON ledger line it was emitted as."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_id: uuid.UUID = Field(..., description="The event's UUID.")
    record: str = Field(
        ...,
        min_length=1,
        description="The canonical JSON line (dump_work_ledger_line), no newline.",
    )
