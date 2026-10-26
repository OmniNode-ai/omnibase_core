# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Invalid Relationship-Reference Reason Enum (OMN-21107, ruling relationships).

Why the work-ledger fold refused a supersedes, amends, extends or corrects
reference. A refused reference creates no link and closes nothing, and it is
listed for a human, as a refused hold release is.
"""

from enum import StrEnum, unique


@unique
class EnumInvalidRelationshipReason(StrEnum):
    """Why a ruling relationship or correction reference was refused."""

    UNKNOWN_TARGET = "unknown_target"
    """The reference names an event_id that is not in the ledger."""

    NOT_A_RULING = "not_a_ruling"
    """A supersedes, amends or extends reference names an event that is neither a
    ruling nor a consent."""


__all__: list[str] = ["EnumInvalidRelationshipReason"]
