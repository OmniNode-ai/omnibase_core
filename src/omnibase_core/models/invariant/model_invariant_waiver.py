# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Waiver model for approved exceptions to architectural invariants."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelInvariantWaiver(BaseModel):
    """An approved, time-bounded exception to an architectural invariant.

    Waivers must have a reviewer and an expiry date. They are not self-issued —
    the approved_exception_id must be a user-issued approval handle.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    approved_exception_receipt: str = Field(
        ...,
        description="User-issued approval receipt handle (not a self-written justification)",
        min_length=1,
    )
    principle_code: str = Field(
        ...,
        description="Invariant principle code this waiver applies to (e.g. ARCH-001)",
        min_length=1,
    )
    expires_at: datetime = Field(
        ...,
        description="Timezone-aware datetime after which this waiver is no longer valid",
    )
    reviewer: str = Field(
        ...,
        description="Identity of the human reviewer who approved the exception",
        min_length=1,
    )
    justification: str = Field(
        ...,
        description="Brief rationale for the exception",
        min_length=1,
    )


__all__ = ["ModelInvariantWaiver"]
