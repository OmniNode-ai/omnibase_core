# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Section of kind ``stage_progress`` (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.models.dashboard.model_view_row_stage_progress import (
    ModelViewRowStageProgress,
)
from omnibase_core.models.dashboard.model_view_section_base import (
    ModelViewSectionBase,
)

__all__ = ["ModelViewSectionStageProgress"]


class ModelViewSectionStageProgress(ModelViewSectionBase):
    """A ``stage_progress`` section: stage progress rows under a stage progress envelope."""

    kind: Literal["stage_progress"] = Field(
        default="stage_progress",
        description="View kind; the document union discriminator",
    )
    rows: tuple[ModelViewRowStageProgress, ...] = Field(
        default=(), description="Stage progress rows; empty when empty_state is set"
    )
