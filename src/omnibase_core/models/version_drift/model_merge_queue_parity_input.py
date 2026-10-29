# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the merge-queue parity check (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_baseline_entry import (
    ModelMergeQueueParityBaselineEntry,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_rules import (
    ModelMergeQueueParityRules,
)

__all__ = ["ModelMergeQueueParityInput"]


class ModelMergeQueueParityInput(BaseModel):
    """A repository's workflow files and its baseline.

    Attributes:
        rules: Trigger names, patterns, bounds and wording from the rule rows.
        files: Repository-relative (path, source) pairs of ``.github/workflows`` files.
        baseline: Pre-existing violations, reported as WARN instead of FAIL.
        report_stale_baseline: When True (a full-tree scan), a baseline entry
            no workflow produces any more is reported as WARN so it is removed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rules: ModelMergeQueueParityRules
    files: tuple[ModelSourceFile, ...] = Field(default=())
    baseline: tuple[ModelMergeQueueParityBaselineEntry, ...] = Field(default=())
    report_stale_baseline: bool = False
