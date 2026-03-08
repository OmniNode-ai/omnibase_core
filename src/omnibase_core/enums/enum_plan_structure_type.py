# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

from enum import Enum

__all__ = ["EnumPlanStructureType", "PlanStructureType"]


class EnumPlanStructureType(str, Enum):
    """Structure type detected in a plan markdown file.

    plan-to-tickets detects these via heading pattern matching.
    TASK_SECTIONS is the canonical format produced by design-to-plan.
    """

    TASK_SECTIONS = "task_sections"
    PHASE_SECTIONS = "phase_sections"
    MILESTONE_TABLE = "milestone_table"
    PRIORITY_LABELS = "priority_labels"
    NUMBERED_LIST = "numbered_list"

    @property
    def is_canonical(self) -> bool:
        """True if this is the preferred format (## Task N:)."""
        return self == EnumPlanStructureType.TASK_SECTIONS


PlanStructureType = EnumPlanStructureType
