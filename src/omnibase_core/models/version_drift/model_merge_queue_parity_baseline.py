# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A repository's merge-queue parity baseline file (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.version_drift.model_merge_queue_parity_baseline_entry import (
    ModelMergeQueueParityBaselineEntry,
)

__all__ = ["ModelMergeQueueParityBaseline"]


class ModelMergeQueueParityBaseline(BaseModel):
    """The pre-existing violations a repository records; the list only shrinks."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str | None = None
    violations: tuple[ModelMergeQueueParityBaselineEntry, ...] = Field(default=())
