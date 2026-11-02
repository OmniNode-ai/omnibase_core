# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Row of a ``line_card`` section (OMN-21997)."""

from __future__ import annotations

from pydantic import Field

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_view_row_base import ModelViewRowBase

__all__ = ["ModelViewRowLineCard"]


class ModelViewRowLineCard(ModelViewRowBase):
    """One production line: its label, severity and status text."""

    label: str = Field(..., min_length=1, description="Line label")
    severity: EnumStatusSeverity = Field(..., description="Upstream severity verdict")
    status_text: str = Field(..., min_length=1, description="Status text for display")
    detail_text: str | None = Field(
        default=None, min_length=1, description="Optional secondary text"
    )
