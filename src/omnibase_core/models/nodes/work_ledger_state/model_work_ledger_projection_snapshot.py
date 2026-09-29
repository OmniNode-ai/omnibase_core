# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The complete work-ledger projection snapshot a reader folds (OMN-20002)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_projection_row import (
    ModelWorkLedgerProjectionRow,
)

__all__ = ["ModelWorkLedgerProjectionSnapshot"]


class ModelWorkLedgerProjectionSnapshot(BaseModel):
    """Every confirmed row of the projection, and the watermark of the last page."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rows: tuple[ModelWorkLedgerProjectionRow, ...] = Field(
        default=(), description="Every page's rows, in the order served."
    )
    applied_offset: int = Field(
        ..., ge=0, description="Watermark: last applied offset."
    )
    end_offset: int = Field(..., ge=0, description="Watermark: stream end offset.")
    lag_records: int = Field(..., ge=0, description="Watermark: records not applied.")
