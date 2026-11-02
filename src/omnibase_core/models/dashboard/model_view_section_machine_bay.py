# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section of kind ``machine_bay`` (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.models.dashboard.model_view_row_machine_bay import (
    ModelViewRowMachineBay,
)
from omnibase_core.models.dashboard.model_view_section_base import (
    ModelViewSectionBase,
)

__all__ = ["ModelViewSectionMachineBay"]


class ModelViewSectionMachineBay(ModelViewSectionBase):
    """A ``machine_bay`` section: machine bay rows under a machine bay envelope."""

    kind: Literal["machine_bay"] = Field(
        default="machine_bay", description="View kind; the document union discriminator"
    )
    rows: tuple[ModelViewRowMachineBay, ...] = Field(
        default=(), description="Machine bay rows; empty when empty_state is set"
    )
