# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Terminal outcome for a concrete delegation terminal."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationTerminalOutcome(StrEnum):
    """The terminal outcome of a delegation attempt."""

    COMPLETED = "completed"
    FAILED = "failed"


__all__: list[str] = ["EnumDelegationTerminalOutcome"]
