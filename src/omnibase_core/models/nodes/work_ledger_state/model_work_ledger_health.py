# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The health summary of a folded work ledger (OMN-19405, typed work ledger T4)."""

from __future__ import annotations

import uuid

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

__all__ = ["ModelWorkLedgerHealth"]


class ModelWorkLedgerHealth(BaseModel):
    """Line and event counts, the last event time, the epoch and the refusals."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    line_count: int = Field(..., ge=0, description="Lines the fold was given.")
    event_count: int = Field(..., ge=0, description="Distinct event_ids.")
    last_event_at: AwareDatetime | None = Field(
        default=None, description="Latest emitted_at. Display only."
    )
    epoch_event_id: uuid.UUID | None = Field(
        default=None, description="event_id of the newest epoch, if any."
    )
    epoch_seq: int | None = Field(
        default=None, description="epoch_seq of the newest epoch, if any."
    )
    holds_in_force_count: int = Field(..., ge=0, description="Holds in force.")
    invalid_release_count: int = Field(..., ge=0, description="Refused releases.")
    undecided_reasons: tuple[str, ...] = Field(
        default=(), description="Every reason the ledger cannot be decided from."
    )
