# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the action-pin check (OMN-17427)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.action_pins.model_action_pin_overlay import (
    ModelActionPinOverlay,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelActionPinCheckInput"]


class ModelActionPinCheckInput(BaseModel):
    """The overlay's rule values and the workflow files to judge.

    Attributes:
        overlay: First-party organisations, tag pattern and known exceptions.
        files: Repository-relative (path, source) pairs of workflow files.
        report_stale_exceptions: When True (a full-tree scan), a known exception
            no file uses any more is reported as WARN so it is removed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overlay: ModelActionPinOverlay
    files: tuple[ModelSourceFile, ...] = Field(default=())
    report_stale_exceptions: bool = False
