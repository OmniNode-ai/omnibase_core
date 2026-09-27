# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed reasons a definition-of-done evaluation does not count as done."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDodEvalRefusal(StrEnum):
    """The first failed conjunct of the definition-of-done predicate."""

    CHECKS_FAILED = "checks_failed"
    STATUS_NOT_VERIFIED = "status_not_verified"
    NO_CHECKS_RUN = "no_checks_run"
    NO_BEHAVIOR_PROVING_CHECK = "no_behavior_proving_check"


__all__ = ["EnumDodEvalRefusal"]
