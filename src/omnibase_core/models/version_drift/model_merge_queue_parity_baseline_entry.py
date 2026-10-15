# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One recorded, pre-existing merge-queue parity violation (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_merge_queue_parity_rule import EnumMergeQueueParityRule

__all__ = ["ModelMergeQueueParityBaselineEntry"]


class ModelMergeQueueParityBaselineEntry(BaseModel):
    """A violation that existed when the gate was introduced.

    The baseline only shrinks: an entry matches by ``(path, job, rule)`` and
    carries the ticket that removes it. ``job`` is ``*`` for a workflow-level
    rule.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(min_length=1)
    job: str = Field(min_length=1)
    rule: EnumMergeQueueParityRule
    ticket: str = Field(pattern=r"^OMN-\d+$")

    def key(self) -> tuple[str, str, str]:
        """The identity a finding is matched on."""
        return (self.path, self.job, self.rule.value)
