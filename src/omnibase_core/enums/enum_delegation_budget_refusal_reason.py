# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Stable reasons a delegation budget is refused before dispatch."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationBudgetRefusalReason(StrEnum):
    """Closed machine-readable pre-dispatch timeout refusal reasons."""

    TIMEOUT_EXCEEDS_TASK_CLASS_CEILING = "timeout_exceeds_task_class_ceiling"


__all__ = ["EnumDelegationBudgetRefusalReason"]
