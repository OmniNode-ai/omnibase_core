# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Invalid-Release Reason Enum (OMN-19405, typed work ledger).

Why the work-ledger fold refused a ``work.hold.released`` event. A refused
release releases nothing: the hold it names stays in force exactly as if the
release had never been recorded, and the refusal is listed for a human.
"""

from enum import StrEnum, unique


@unique
class EnumInvalidReleaseReason(StrEnum):
    """Why a hold release was refused by the fold."""

    UNKNOWN_HOLD = "unknown_hold"
    """The release names an event_id that is not in the ledger."""

    NOT_A_HOLD = "not_a_hold"
    """The release names an event that is not a ``work.hold.placed``."""

    NOT_SUBSET = "not_subset"
    """The partial scope reaches outside the scope of the hold it names."""

    REAP_WITHOUT_LEASE = "reap_without_lease"
    """A reap names a hold that carries no ``expires_at``, so it is not a lease."""

    MISSING_SURFACE_RESULT = "missing_surface_result"
    """The release lifts a surface but records no surface outcome."""


__all__: list[str] = ["EnumInvalidReleaseReason"]
