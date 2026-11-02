# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Row of a ``stop`` section (OMN-21997)."""

from __future__ import annotations

from typing import Self

from pydantic import AwareDatetime, Field, model_validator

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_view_row_base import ModelViewRowBase

__all__ = ["ModelViewRowStop"]


class ModelViewRowStop(ModelViewRowBase):
    """A stoppage: its reason and when it began and ended."""

    label: str = Field(..., min_length=1, description="What stopped")
    reason_text: str = Field(..., min_length=1, description="Reason for the stop")
    severity: EnumStatusSeverity = Field(..., description="Upstream severity verdict")
    started_at: AwareDatetime = Field(..., description="When the stop began")
    ended_at: AwareDatetime | None = Field(
        default=None, description="When the stop ended; None while it continues"
    )

    @model_validator(mode="after")
    def validate_stop_ends_after_it_starts(self) -> Self:
        """Require a stop to end no earlier than it began.

        Raises:
            ValueError: If ``ended_at`` is before ``started_at``.
        """
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at must not be before started_at")
        return self
