# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Outcome of one evidence unit at a skill seam (OMN-21627)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumEvidenceUnitOutcome(UtilStrValueHelper, str, Enum):
    """What a skill seam knows about one eligible unit (a draft, a claim opportunity or an approval intent).

    Attributes:
        ACCEPTED: Accepted at independent verification with no material correction.
        CORRECTED: Accepted only after a material correction or a preventable reissue.
        SAFETY_FAILURE: An unauthorized, false or duplicated effect is confirmed.
        PENDING: Due but not yet matured.
        MISSING: Expected from the intake source and not captured.
        UNASSESSED: Captured but not yet assessed.
    """

    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    SAFETY_FAILURE = "safety_failure"
    PENDING = "pending"
    MISSING = "missing"
    UNASSESSED = "unassessed"
