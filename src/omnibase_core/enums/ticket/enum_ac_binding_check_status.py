# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Status of the check a binding row names (OMN-18056, moved to core by OMN-20368).

Mirrors the dod_verify per-check statuses a Done-write gate can be handed, plus
the honest sixth: a status the verifier reported that this enum does not know.
Typed rather than a bare string because the whole point of a binding row is
that ONE of these values -- ``VERIFIED`` -- discharges a criterion and the rest
do not, and a comparison that decides that must not be a string literal.
"""

from __future__ import annotations

from enum import StrEnum


class EnumAcBindingCheckStatus(StrEnum):
    """What the declaring check's dod_verify run concluded."""

    VERIFIED = "verified"
    NON_PROBATIVE = "non_probative"
    SKIPPED = "skipped"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"

    @classmethod
    def from_verdict(cls, raw: str) -> EnumAcBindingCheckStatus:
        """Parse a verdict's status string, falling back to UNKNOWN."""
        try:
            return cls(raw.strip().lower())
        except ValueError:
            return cls.UNKNOWN


__all__ = ["EnumAcBindingCheckStatus"]
