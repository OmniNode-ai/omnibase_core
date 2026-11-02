# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section of kind ``stop`` (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.models.dashboard.model_view_row_stop import (
    ModelViewRowStop,
)
from omnibase_core.models.dashboard.model_view_section_base import (
    ModelViewSectionBase,
)

__all__ = ["ModelViewSectionStop"]


class ModelViewSectionStop(ModelViewSectionBase):
    """A ``stop`` section: stop rows under a stop envelope."""

    kind: Literal["stop"] = Field(
        default="stop", description="View kind; the document union discriminator"
    )
    rows: tuple[ModelViewRowStop, ...] = Field(
        default=(), description="Stop rows; empty when empty_state is set"
    )
