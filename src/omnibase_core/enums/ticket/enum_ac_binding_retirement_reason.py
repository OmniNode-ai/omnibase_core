# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Why a contract retires an acceptance-criterion binding (OMN-21220)."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumAcBindingRetirementReason(StrEnum):
    """The closed reasons a ``supersedes_ac_binding`` entry may give.

    SUPERSEDED_BY: another item in the contract now binds the label.
    NO_LONGER_APPLICABLE: nothing replaces it; the criterion no longer needs it.
    """

    SUPERSEDED_BY = "superseded_by"
    NO_LONGER_APPLICABLE = "no_longer_applicable"


__all__ = ["EnumAcBindingRetirementReason"]
