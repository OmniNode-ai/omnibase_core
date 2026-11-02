# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Row of a ``machine_bay`` section (OMN-21997)."""

from __future__ import annotations

from pydantic import Field

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_view_row_base import ModelViewRowBase

__all__ = ["ModelViewRowMachineBay"]


class ModelViewRowMachineBay(ModelViewRowBase):
    """One machine bay and its current state."""

    bay_label: str = Field(..., min_length=1, description="Bay label")
    machine_label: str | None = Field(
        default=None, min_length=1, description="Label of the machine in the bay"
    )
    severity: EnumStatusSeverity = Field(..., description="Upstream severity verdict")
    state_text: str = Field(..., min_length=1, description="State text for display")
