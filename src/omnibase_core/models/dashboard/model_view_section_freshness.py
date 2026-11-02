# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section of kind ``freshness`` (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.models.dashboard.model_view_row_freshness import (
    ModelViewRowFreshness,
)
from omnibase_core.models.dashboard.model_view_section_base import (
    ModelViewSectionBase,
)

__all__ = ["ModelViewSectionFreshness"]


class ModelViewSectionFreshness(ModelViewSectionBase):
    """A ``freshness`` section: freshness rows under a freshness envelope."""

    kind: Literal["freshness"] = Field(
        default="freshness", description="View kind; the document union discriminator"
    )
    rows: tuple[ModelViewRowFreshness, ...] = Field(
        default=(), description="Freshness rows; empty when empty_state is set"
    )
