# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Row of a ``stage_progress`` section (OMN-21997)."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from omnibase_core.models.dashboard.model_view_row_base import ModelViewRowBase

__all__ = ["ModelViewRowStageProgress"]


class ModelViewRowStageProgress(ModelViewRowBase):
    """Where one item stands within an ordered set of stages."""

    label: str = Field(..., min_length=1, description="Item label")
    stage_label: str = Field(..., min_length=1, description="Name of the current stage")
    stage_index: int = Field(..., ge=0, description="Zero-based index of the stage")
    stage_count: int = Field(..., ge=1, description="Number of stages")

    @model_validator(mode="after")
    def validate_stage_index_within_count(self) -> Self:
        """Require the stage index to name one of the stages.

        Raises:
            ValueError: If ``stage_index`` is not less than ``stage_count``.
        """
        if self.stage_index >= self.stage_count:
            raise ValueError(
                f"stage_index {self.stage_index} must be less than stage_count "
                f"{self.stage_count}"
            )
        return self
