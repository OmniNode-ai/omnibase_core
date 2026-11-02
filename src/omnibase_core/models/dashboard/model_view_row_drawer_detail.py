# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Row of a ``drawer_detail`` section (OMN-21997)."""

from __future__ import annotations

from pydantic import Field

from omnibase_core.models.dashboard.model_view_detail_entry import ModelViewDetailEntry
from omnibase_core.models.dashboard.model_view_row_base import ModelViewRowBase

__all__ = ["ModelViewRowDrawerDetail"]


class ModelViewRowDrawerDetail(ModelViewRowBase):
    """Labelled detail entries for one drawer."""

    title: str = Field(..., min_length=1, description="Drawer title")
    entries: tuple[ModelViewDetailEntry, ...] = Field(
        ..., min_length=1, description="Labelled detail entries"
    )
