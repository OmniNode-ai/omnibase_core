# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Final-content verdict on a delegation terminal."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationContentVerdict(StrEnum):
    """Whether the final terminal content can be used as delivered."""

    CORRECT = "correct"
    USABLE = "usable"
    UNUSABLE = "unusable"
    NOT_APPLICABLE = "not_applicable"
    UNDETERMINED = "undetermined"


__all__ = ["EnumDelegationContentVerdict"]
