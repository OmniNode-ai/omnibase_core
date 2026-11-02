# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section of kind ``drawer_detail`` (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.models.dashboard.model_view_row_drawer_detail import (
    ModelViewRowDrawerDetail,
)
from omnibase_core.models.dashboard.model_view_section_base import (
    ModelViewSectionBase,
)

__all__ = ["ModelViewSectionDrawerDetail"]


class ModelViewSectionDrawerDetail(ModelViewSectionBase):
    """A ``drawer_detail`` section: drawer detail rows under a drawer detail envelope."""

    kind: Literal["drawer_detail"] = Field(
        default="drawer_detail",
        description="View kind; the document union discriminator",
    )
    rows: tuple[ModelViewRowDrawerDetail, ...] = Field(
        default=(), description="Drawer detail rows; empty when empty_state is set"
    )
