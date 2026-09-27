# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Normalized terminal and pending statuses consumed by DoD evaluation."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDodEvalVerificationStatus(StrEnum):
    """Status vocabulary for a definition-of-done evaluation input."""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNRESOLVED = "unresolved"


__all__ = ["EnumDodEvalVerificationStatus"]
