# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Outcomes supported by an evidence verification check or aggregate."""

from enum import StrEnum, unique


@unique
class EnumEvidenceVerificationStatus(StrEnum):
    """Distinguish an established failure from a probe that learnt nothing."""

    PASS = "PASS"
    """Every required observation was established and passed."""

    FAIL = "FAIL"
    """An observation established that a check failed."""

    INDETERMINATE = "INDETERMINATE"
    """No check failed, but an observation could not be established."""


__all__ = ["EnumEvidenceVerificationStatus"]
