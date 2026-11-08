# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Where a delegation run's task-class timeout ceiling was read from."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationCeilingSource(StrEnum):
    """Closed origin of a task-class timeout ceiling."""

    PACKAGED = "packaged"
    OVERLAY = "overlay"


__all__ = ["EnumDelegationCeilingSource"]
