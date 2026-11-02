# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section of kind ``line_card`` (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.models.dashboard.model_view_row_line_card import (
    ModelViewRowLineCard,
)
from omnibase_core.models.dashboard.model_view_section_base import (
    ModelViewSectionBase,
)

__all__ = ["ModelViewSectionLineCard"]


class ModelViewSectionLineCard(ModelViewSectionBase):
    """A ``line_card`` section: line card rows under a line card envelope."""

    kind: Literal["line_card"] = Field(
        default="line_card", description="View kind; the document union discriminator"
    )
    rows: tuple[ModelViewRowLineCard, ...] = Field(
        default=(), description="Line card rows; empty when empty_state is set"
    )
