# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Budget policy outcome enum for the delegation compliance loop."""

from __future__ import annotations

from enum import StrEnum


class EnumBudgetAction(StrEnum):
    """Budget policy outcome used by the compliance loop."""

    CONTINUE = "CONTINUE"
    WARN = "WARN"
    THROTTLE = "THROTTLE"
    ABORT = "ABORT"


__all__: list[str] = ["EnumBudgetAction"]
